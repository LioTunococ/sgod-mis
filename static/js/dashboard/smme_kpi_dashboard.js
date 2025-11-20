// Externalized SMME KPI Dashboard Script (initial extraction)
// NOTE: Dynamic Django template values now provided via window.SMME_DASHBOARD_CONFIG.
// kpiData server-side bootstrap removed; data comes from API fetch.

(function(){
  const CFG = window.SMME_DASHBOARD_CONFIG || {};
  const FILTERS_FORM_ID = 'filtersBody';
  function getFiltersForm(){ return document.getElementById(FILTERS_FORM_ID); }

  // ----- Helpers -----
  function currentQuery(){
    const form = getFiltersForm();
    if(!form) return new URLSearchParams();
    return new URLSearchParams(new FormData(form));
  }
  function updateCsvLink(params){
    const link = document.getElementById('exportCsvBtn');
    if(!link) return;
    const url = new URL(link.href, window.location.origin);
    url.search = params.toString();
    link.href = url.toString();
  }
  function updateActiveFiltersBadge(){
    const chips = document.querySelectorAll('#activeFilterChips .chip');
    const badge = document.getElementById('activeFiltersCount');
    if(badge) badge.textContent = String(chips.length);
  }
  function perfClass(pct){
    const v = Number(pct||0); if(v>=75) return 'performance-high'; if(v>=50) return 'performance-medium'; return 'performance-low';
  }
  function captureBarState(){
    const state = new Map();
    document.querySelectorAll('.kpi-bar-fill[data-key]').forEach(el => {
      try {
        const parent = el.parentElement;
        const w = parseFloat(getComputedStyle(el).width||'0');
        const pct = parent && parent.clientWidth ? (w/parent.clientWidth)*100 : 0;
        state.set(el.dataset.key, pct);
      } catch(_){}
    });
    return state;
  }
  function animateBars(prev){
    document.querySelectorAll('.kpi-bar-fill[data-key]').forEach(el => {
      const key = el.dataset.key; const final = parseFloat((el.style.width||'0').replace('%','')); const start = prev.has(key)?prev.get(key):0;
      el.style.width = start+'%'; requestAnimationFrame(()=>{ el.style.width = final+'%'; });
    });
  }
  function highlightSortedColumn(){
    const params = currentQuery(); const sortKey = (params.get('sort_by')||'').trim();
    ['clientRenderedContent','serverRenderedContent'].map(id=>document.getElementById(id)).filter(Boolean).forEach(scope=>{
      scope.querySelectorAll('th.sorted-col, td.sorted-col').forEach(el=>el.classList.remove('sorted-col'));
      const th = scope.querySelector(`th.sortable[data-sort="${sortKey}"]`); if(!th) return; th.classList.add('sorted-col');
      const idx = Array.from(th.parentElement.children).indexOf(th)+1; scope.querySelectorAll(`tbody tr td:nth-child(${idx})`).forEach(td=>td.classList.add('sorted-col'));
    });
  }
  function applyQuickSearchFilter(){
    const input = document.getElementById('quickSearch'); if(!input) return; const q=(input.value||'').toLowerCase().trim();
    const scope = (document.getElementById('clientRenderedContent')?.style.display!=='none') ? document.getElementById('clientRenderedContent') : document.getElementById('serverRenderedContent');
    if(!scope) return;
    scope.querySelectorAll('table.kpi-table').forEach(tbl=>{
      tbl.querySelectorAll('tbody tr').forEach(tr=>{
        if(tr.classList.contains('group-header')) return;
        const schoolEl = tr.querySelector('.school-name'); const districtEl = tr.querySelector('.district-name');
        const school = (schoolEl?.getAttribute('data-plain')||schoolEl?.textContent||'').toLowerCase();
        const district = (districtEl?.getAttribute('data-plain')||districtEl?.textContent||'').toLowerCase();
        const match = !q || school.includes(q) || district.includes(q);
        tr.style.display = match?'':'none';
        if(match){
          const re = q? new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'),'ig'):null;
          [schoolEl,districtEl].forEach(el=>{ if(!el) return; const plain = el.getAttribute('data-plain')||el.textContent; el.setAttribute('data-plain',plain); if(!q){ el.innerHTML=plain; return;} el.innerHTML = plain.replace(re,m=>`<mark class="q">${m}</mark>`); });
        }
      });
    });
  }

  // ----- Renderers (subset for overview + others) -----
  function renderOverview(results){
    const kpiSelect = document.getElementById('kpi_part');
    const currentKpi = kpiSelect? kpiSelect.value : 'all';
    if(currentKpi==='implementation'){
      const headers = `<thead><tr><th>School</th><th>District</th><th>Level</th><th>% Implementation</th><th>Access</th><th>Quality</th><th>Equity</th><th>Enabling</th></tr></thead>`;
      const rows = results.map(r=>`<tr><td class="school-name">${r.school_name}</td><td class="district-name">${r.district||''}</td><td>${r.school_level||''}</td><td><div class="kpi-bar-cell"><div class="kpi-bar-fill ${perfClass(r.implementation)} kpi-implementation" data-key="${r.school_id||r.school_name}-impl" style="width:${r.implementation||0}%"></div><span class="kpi-bar-text">${r.implementation||0}%</span></div></td><td>${r.impl_access||0}%</td><td>${r.impl_quality||0}%</td><td>${r.impl_equity||0}%</td><td>${r.impl_enabling||0}%</td></tr>`).join('');
      return `<table class="kpi-table">${headers}<tbody>${rows||`<tr><td colspan="8" style="text-align:center; padding:2rem; color:#6b7280;">No data.</td></tr>`}</tbody></table>`;
    }
    const headers = `<thead><tr><th>School</th><th>District</th><th>Level</th><th>% Impl</th><th>SLP</th><th>CRLA</th><th>PHILIRI</th><th>RMA</th><th>Supervision</th><th>ADM</th></tr></thead>`;
    const rows = results.map(r=>`<tr><td class="school-name">${r.school_name}</td><td class="district-name">${r.district||''}</td><td>${r.school_level||''}</td><td><div class="kpi-bar-cell"><div class="kpi-bar-fill ${perfClass(r.implementation)} kpi-implementation" data-key="${r.school_id||r.school_name}-impl" style="width:${r.implementation||0}%"></div><span class="kpi-bar-text">${r.implementation||0}%</span></div></td><td><div class="kpi-bar-cell"><div class="kpi-bar-fill ${perfClass(r.slp)} kpi-slp" data-key="${r.school_id||r.school_name}-slp" style="width:${r.slp||0}%"></div><span class="kpi-bar-text">${r.slp||0}%</span></div></td><td>${r.reading_crla||0}%</td><td>${r.reading_philiri||0}%</td><td>${r.rma||0}%</td><td>${r.supervision||0}%</td><td>${r.adm||0}%</td></tr>`).join('');
    return `<table class="kpi-table">${headers}<tbody>${rows||`<tr><td colspan="10" style="text-align:center; padding:2rem; color:#6b7280;">No data.</td></tr>`}</tbody></table>`;
  }

  // Placeholder minimal renderers for other views (extend later if needed)
  function renderSimpleBands(results, bands){
    const headers = `<thead><tr><th>School</th><th>District</th>${bands.map(b=>`<th>${b}</th>`).join('')}</tr></thead>`;
    const rows = results.map(r=>`<tr><td class="school-name">${r.school_name}</td><td class="district-name">${r.district||''}</td>${bands.map(b=>`<td>${r[b]||0}%</td>`).join('')}</tr>`).join('');
    return `<table class="kpi-table">${headers}<tbody>${rows||`<tr><td colspan="${bands.length+2}" style="text-align:center; padding:2rem; color:#6b7280;">No data.</td></tr>`}</tbody></table>`;
  }

  // ----- Summary helpers -----
  function updateSummaryFromApi(view, results){
    const schoolsEl = document.querySelector('.summary-section .summary-grid .summary-card:nth-child(1) h3');
    const pointsEl = document.querySelector('.summary-section .summary-grid .summary-card:nth-child(2) h3');
    if(!schoolsEl||!pointsEl) return; const uniq=new Set(); results.forEach(r=>uniq.add(r.school_id||r.id));
    schoolsEl.textContent = String(uniq.size); pointsEl.textContent = String(results.length);
    const exportCount=document.getElementById('export-schools-count'); if(exportCount) exportCount.textContent = String(uniq.size);
  }

  // ----- SLOP Summary Renderer (Table) -----
  function updateSlopSummary(results){
    const container = document.getElementById('slopSummary');
    if(!container) return;
    if(!results || !results.length){ container.style.display='none'; return; }
    const keys = {
      a: 'slop_prereq_count',
      b: 'slop_llc_difficult_count',
      c: 'slop_llc_not_covered_count',
      d: 'slop_sped_needs_count',
      e: 'slop_reading_link_count',
      f: 'slop_other_count'
    };
    const totals = { a:0,b:0,c:0,d:0,e:0,f:0 };
    const schoolsWithReason = { a:new Set(),b:new Set(),c:new Set(),d:new Set(),e:new Set(),f:new Set() };
    let totalRowsConsidered = 0; const uniqueSchools = new Set();
    results.forEach(r=>{
      const sid = r.school_id||r.id; if(sid) uniqueSchools.add(sid);
      let anyReason = false;
      Object.entries(keys).forEach(([code, field])=>{
        const val = Number(r[field]||0);
        if(val>0){ anyReason = true; totals[code]+=val; if(sid) schoolsWithReason[code].add(sid); }
      });
      if((r.slp||0)>0 || anyReason) totalRowsConsidered += 1;
    });
    // Populate table cells
    Object.entries(totals).forEach(([code,val])=>{
      const countEl = document.getElementById(`slop_${code}_count`); if(countEl) countEl.textContent = String(val);
      const schoolsEl = document.getElementById(`slop_${code}_schools`); if(schoolsEl) schoolsEl.textContent = String(schoolsWithReason[code].size);
    });
    const totalEl = document.getElementById('slopTotalRows'); if(totalEl) totalEl.textContent = String(totalRowsConsidered);
    const totalSchoolsEl = document.getElementById('slopTotalSchools'); if(totalSchoolsEl) totalSchoolsEl.textContent = String(uniqueSchools.size);
    container.style.display='block';
  }

  // ----- AJAX -----
  let lastAbort=null;
  async function doAjaxUpdate(){
    const client=document.getElementById('clientRenderedContent'); const server=document.getElementById('serverRenderedContent'); const loader=document.getElementById('ajaxLoader');
    if(!client||!server) return;
    const params=currentQuery(); if(lastAbort) lastAbort.abort(); lastAbort=new AbortController(); const signal=lastAbort.signal;
    server.style.display='none'; client.style.display='none'; loader.style.display='block';
    const apiUrl=new URL(CFG.apiUrl||'/smme/api/', window.location.origin); params.set('page','1'); params.set('page_size','10000'); apiUrl.search=params.toString();
    try {
      const prev=captureBarState(); const res=await fetch(apiUrl.toString(),{signal,credentials:'same-origin',headers:{'Accept':'application/json'}});
      if(!res.ok) throw new Error('HTTP '+res.status); const data=await res.json(); const view=data.view||params.get('kpi_part')||'all'; const results=data.results||[];
      let html='';
      if(view==='all'||view==='implementation') html=renderOverview(results);
      else if(view==='slp') html=renderSimpleBands(results,['dnme','fs','s','vs','o']);
      else if(view.startsWith('reading')) html=renderSimpleBands(results, view.includes('philiri')? ['frustration_pct','instructional_pct','independent_pct'] : ['low_emerging_pct','high_emerging_pct','developing_pct','transitioning_pct']);
      else if(view==='rma') html=renderSimpleBands(results,['not_proficient_pct','low_proficient_pct','nearly_proficient_pct','proficient_pct','at_grade_level_pct']);
      else if(view==='supervision') html=renderSimpleBands(results,['percent_ta']);
      else if(view==='adm') html=renderSimpleBands(results,['overall_adm']);
      else html=renderOverview(results);
      client.innerHTML=html; loader.style.display='none'; client.style.display='block'; animateBars(prev); updateSummaryFromApi(view, results); updateCsvLink(params); updateActiveFiltersBadge(); applyQuickSearchFilter(); highlightSortedColumn();
      // SLOP summary only shown when filtering by SLP
      if(view==='slp'){ updateSlopSummary(results); } else { const c=document.getElementById('slopSummary'); if(c) c.style.display='none'; }
      const newUrl=new URL(window.location.href); newUrl.search=params.toString(); window.history.replaceState({},'',newUrl.toString());
    } catch(e){ loader.style.display='none'; server.style.display='block'; console.error('AJAX update failed', e); }
  }

  // ----- Events -----
  function wireEvents(){
    const form=getFiltersForm(); if(form){
      let submitTimer=null; function debounce(){ if(submitTimer) clearTimeout(submitTimer); submitTimer=setTimeout(()=>doAjaxUpdate(),250); }
      form.addEventListener('submit',e=>{ e.preventDefault(); doAjaxUpdate(); });
      form.addEventListener('change',()=>debounce());
      form.addEventListener('input',e=>{ const t=e.target; if(t && t.matches('input[type="number"], input[type="text"], select')) debounce(); });
    }
    document.querySelectorAll('th.sortable').forEach(th=>{
      th.addEventListener('click',()=>{
        const sortBy=th.getAttribute('data-sort'); const sortByInput=document.getElementById('sort_by'); const sortDirInput=document.getElementById('sort_dir');
        if(!sortByInput||!sortDirInput) return; if(sortByInput.value===sortBy) sortDirInput.value = (sortDirInput.value==='asc')?'desc':'asc'; else { sortByInput.value=sortBy; sortDirInput.value='asc'; }
        doAjaxUpdate();
      });
    });
    const legendModal=document.getElementById('legendModal'); const openBtn=document.getElementById('openLegendBtn'); const closeBtn=document.getElementById('closeLegendBtn');
    function toggleLegend(show){ if(!legendModal) return; legendModal.style.display=show?'block':'none'; }
    if(openBtn) openBtn.addEventListener('click',()=>toggleLegend(true)); if(closeBtn) closeBtn.addEventListener('click',()=>toggleLegend(false));
    if(legendModal){ legendModal.addEventListener('click',e=>{ if(e.target===legendModal) toggleLegend(false); }); document.addEventListener('keydown',e=>{ if(e.key==='Escape') toggleLegend(false); }); }
    const quickSearch=document.getElementById('quickSearch'); if(quickSearch) quickSearch.addEventListener('input',applyQuickSearchFilter);
  }

  // ----- Charts -----
  function initializeSLPTrendChart(){
    if(!CFG.showAnalytics || CFG.isSlpDetail) return; const el=document.getElementById('slpTrendChart'); if(!el) return; if(typeof Chart==='undefined') return;
    const trend = CFG.slpTrendData || []; const labels=trend.map(x=>x.quarter); const datasets=[
      { label:'DNME', data:trend.map(x=>x.dnme_pct), borderColor:'#ef4444', backgroundColor:'rgba(239,68,68,.15)', tension:.25 },
      { label:'FS', data:trend.map(x=>x.fs_pct), borderColor:'#f59e0b', backgroundColor:'rgba(245,158,11,.15)', tension:.25 },
      { label:'S', data:trend.map(x=>x.s_pct), borderColor:'#facc15', backgroundColor:'rgba(250,204,21,.15)', tension:.25 },
      { label:'VS', data:trend.map(x=>x.vs_pct), borderColor:'#84cc16', backgroundColor:'rgba(132,204,22,.15)', tension:.25 },
      { label:'O', data:trend.map(x=>x.o_pct), borderColor:'#3b82f6', backgroundColor:'rgba(59,130,246,.15)', tension:.25 }
    ];
    new Chart(el.getContext('2d'),{ type:'line', data:{labels,datasets}, options:{ responsive:true, maintainAspectRatio:false, interaction:{mode:'index',intersect:false}, stacked:false, plugins:{ legend:{position:'bottom'} }, scales:{ y:{beginAtZero:true,max:100,ticks:{ callback:v=>v+'%'}} } } });
  }

  // ----- Init -----
  document.addEventListener('DOMContentLoaded',()=>{
    wireEvents(); updateActiveFiltersBadge(); highlightSortedColumn(); doAjaxUpdate(); if(CFG.showAnalytics) initializeSLPTrendChart();
  });
})();
