"""Embed shared, offline theme controls into every generated result page."""
from pathlib import Path

def apply_theme(page):
    if 'id="workbench-theme-style"' in page:return page
    assets=Path(__file__).parents[1]/'assets'
    css=(assets/'theme.css').read_text(encoding='utf-8')
    js=(assets/'theme.js').read_text(encoding='utf-8')
    style='<style id="workbench-theme-style">'+css+'</style>'
    page=page.replace('</head>',style+'</head>',1) if '</head>' in page else page.replace('<body>',style+'<body>',1)
    return page.replace('</body>','<script data-workbench-theme>'+js+'</script></body>',1)
