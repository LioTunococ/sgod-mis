from pyjsparser import PyJsParser
from pathlib import Path
code = Path('static/js/submission-form.js').read_text(encoding='utf-8')
parser = PyJsParser()
try:
    parser.parse(code)
    print('ok')
except Exception as exc:
    print(type(exc).__name__)
    print(exc)
