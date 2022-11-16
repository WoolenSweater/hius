HEADER = '''
<head>
  <title>{title}</title>
  {favicon}
  <meta charset='utf-8'/>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <link href='https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700' rel='stylesheet'>
  <script src='https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js' crossorigin></script>
  <style>body {{ margin: 0; padding: 0 }}</style>
</head>
'''

BODY = '''
<body>
  <div id='redoc-container'/>
  <script type='text/javascript'>
    Redoc.init(
      JSON.parse('{schema}'),
      undefined,
      document.getElementById('redoc-container')
    )
  </script>
</body>
'''

HTML = '''
<!DOCTYPE html>
<html>
  {header}
  {body}
</html>
'''
