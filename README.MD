# Required Libraries for parsing HTML and SSL

pip install --user beautifulsoup4 certifi


# Running

Right now, the script needs to be in a relative directory to where /public_html/directory1.html is located.  I can't figure out why the aliasing to student directories isn't mapping properly /u/&SYSUID/public_html/ -> /z/&SYSUID/public_html

So, at the moment, the script finds students.json in the same directory as the python script, and public_html as ../public_html

Directory structure something like:
```
/py/badges.py
/py/students.json
/public_html/directory1.html
```
