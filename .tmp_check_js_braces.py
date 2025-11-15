import sys,re
path='static/js/submission-form.js'
text=open(path,'r',encoding='utf-8').read()
line_starts=[0]
for i,ch in enumerate(text):
    if ch=='\n':
        line_starts.append(i+1)
# simple parser ignoring content in //, /* */, ' ', " ", and `template` with ${}
S_NORMAL,S_SQ,S_DQ,S_BT,S_BLOCK_COMMENT,S_LINE_COMMENT=range(6)
state=S_NORMAL
stack=[]
errors=[]
i=0
while i<len(text):
    ch=text[i]
    ch2=text[i:i+2]
    # handle state
    if state==S_NORMAL:
        if ch2=='/*':
            state=S_BLOCK_COMMENT; i+=2; continue
        if ch2=='//':
            state=S_LINE_COMMENT; i+=2; continue
        if ch=="'":
            state=S_SQ; i+=1; continue
        if ch=='"':
            state=S_DQ; i+=1; continue
        if ch=='`':
            state=S_BT; i+=1; continue
        if ch in '([{':
            stack.append((ch,i)); i+=1; continue
        if ch in ')]}':
            if not stack:
                errors.append(('unmatched_closer',ch,i))
            else:
                opener,pos=stack.pop()
                pairs={'(' : ')','[':']','{':'}'}
                if pairs[opener]!=ch:
                    errors.append(('mismatch',opener,pos,ch,i))
            i+=1; continue
        i+=1; continue
    elif state==S_LINE_COMMENT:
        if ch=='\n': state=S_NORMAL
        i+=1; continue
    elif state==S_BLOCK_COMMENT:
        if ch2=='*/': state=S_NORMAL; i+=2; continue
        i+=1; continue
    elif state==S_SQ:
        if ch=='\\': i+=2; continue
        if ch=="'": state=S_NORMAL; i+=1; continue
        i+=1; continue
    elif state==S_DQ:
        if ch=='\\': i+=2; continue
        if ch=='"': state=S_NORMAL; i+=1; continue
        i+=1; continue
    elif state==S_BT:
        if ch=='\\': i+=2; continue
        if ch=='`': state=S_NORMAL; i+=1; continue
        # handle ${ ... }
        if ch=='$' and i+1<len(text) and text[i+1]=='{':
            # enter expression: push a special marker for template expr
            stack.append(('{',i))
            i+=2; continue
        # otherwise normal template content
        i+=1; continue
# Report
print('Remaining stack:',len(stack))
for item in stack[-10:]:
    ch,pos=item
    # find line
    line=1
    for idx,s in enumerate(line_starts):
        if s>pos:
            line=idx
            break
    else:
        line=len(line_starts)
    print('Unclosed',ch,'opened at line',line)
print('Errors count:',len(errors))
for e in errors[:10]:
    if e[0]=='unmatched_closer':
        _,ch,pos=e
        line=1
        for idx,s in enumerate(line_starts):
            if s>pos:
                line=idx
                break
        else:
            line=len(line_starts)
        print('Unmatched closer',ch,'at line',line)
    else:
        _,op,oppos,ch,clpos=e
        line=1
        for idx,s in enumerate(line_starts):
            if s>clpos:
                line=idx
                break
        else:
            line=len(line_starts)
        print('Mismatch',op,'...',ch,'closing at line',line)
