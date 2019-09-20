import os

url = os.popen("gp url 8888").read()

c = get_config()
#c.Spawner.args = ['--NotebookApp.tornado_settings={"headers":{"Content-Security-Policy": "frame-ancestors * self '" + url + "'"}}']
c.NotebookApp.tornado_settings = { 'headers': { 'Content-Security-Policy': "frame-ancestors * 'self' '" + url + "'" } }

