from pyslideshare import pyslideshare

# Have all the secure keys in a file called localsettings.py
try:
    from localsettings import username, password, api_key, secret_key, proxy
except:
    pass
    
obj = pyslideshare.pyslideshare(locals(), verbose=False)
json = obj.get_slideshow(slideshow_id=436333)
if not json:
    import sys
    print('No response. Perhaps slideshare down?', file=sys.stderr)
    sys.exit(1)

show = json.Slideshows.Slideshow
print('Name : %s, Permalink : %s' % (show.Title, show.Permalink))