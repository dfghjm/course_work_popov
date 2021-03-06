# pyslideshare.py
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Slideshare documentation - http://www.slideshare.net/developers/documentation

import urllib.request, urllib.parse, urllib.error, urllib.request, urllib.error, urllib.parse
import mimetypes
import email.generator
import os, stat, time, sys
from io import StringIO

import socket

from xml2dict import fromstring

# Sometimes slideshare doesn't response quick enough!
# timeout in seconds
timeout = 15
socket.setdefaulttimeout(timeout)

service_url_dict = {
    'slideshow_by_user' : 'https://www.slideshare.net/api/1/get_slideshow_by_user',
    'get_slideshow' : 'https://www.slideshare.net/api/1/get_slideshow',
    'slideshow_by_tag' : 'https://www.slideshare.net/api/1/get_slideshow_by_tag',
    'upload_slideshow' : 'https://www.slideshare.net/api/1/upload_slideshow',
    'delete_slideshow' : 'https://www.slideshare.net/api/1/delete_slideshow',
}

class Callable:
    def __init__(self, anycallable):
        self.__call__ = anycallable

# Controls how sequences are uncoded. If true, elements may be given multiple values by
#  assigning a sequence.
doseq = 1

# Inspiration from http://peerit.blogspot.com/2007/07/multipartposthandler-doesnt-work-for.html
# Added few bug fixes
class MultipartPostHandler(urllib.request.BaseHandler):
    handler_order = urllib.request.HTTPHandler.handler_order - 10 # needs to run first

    def http_request(self, request):
        data = request.get_data()
        if data is not None and type(data) != str:
            v_files = []
            v_vars = []
            try:
                 for(key, value) in list(data.items()):
                     if type(value) == file:
                         v_files.append((key, value))
                     else:
                         v_vars.append((key, value))
            except TypeError:
                systype, value, traceback = sys.exc_info()
                raise TypeError("not a valid non-string sequence or mapping object").with_traceback(traceback)

            if len(v_files) == 0:
                data = urllib.parse.urlencode(v_vars, doseq)
            else:
                boundary, data = self.multipart_encode(v_vars, v_files)

                contenttype = 'multipart/form-data; boundary=%s' % boundary
                if(request.has_header('Content-Type')
                   and request.get_header('Content-Type').find('multipart/form-data') != 0):
                    print("Replacing %s with %s" % (request.get_header('content-type'), 'multipart/form-data'))
                request.add_unredirected_header('Content-Type', contenttype)
            request.add_data(data)       
        return request

    def multipart_encode(self, vars, files, boundary = None, buf = None):
        if boundary is None:
            boundary = email.generator._make_boundary()
        if buf is None:
            buf = StringIO()
        for(key, value) in vars:
            buf.write('--%s\r\n' % boundary)
            buf.write('Content-Disposition: form-data; name="%s"' % key)
            buf.write('\r\n\r\n' + str(value) + '\r\n')
        for(key, fd) in files:
            file_size = os.fstat(fd.fileno())[stat.ST_SIZE]
            filename = fd.name.split('/')[-1]
            contenttype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
            buf.write('--%s\r\n' % boundary)
            buf.write('Content-Disposition: form-data; name="%s"; filename="%s"\r\n' % (key, filename))
            buf.write('Content-Type: %s\r\n' % contenttype)
            # buffer += 'Content-Length: %s\r\n' % file_size
            fd.seek(0)
            buf.write('\r\n' + fd.read() + '\r\n')
        buf.write('--' + boundary + '--\r\n\r\n')
        buf = buf.getvalue()
        return boundary, buf
    multipart_encode = Callable(multipart_encode)
    https_request = http_request
    
class pyslideshare:
    
    def __init__(self, params_dict, verbose=False, proxy=None):
        if 'api_key' not in params_dict or 'secret_key' not in params_dict:
            print('Both Api key and secret key are required.', file=sys.stderr)
            sys.exit(1)
        self.params = params_dict
        self.verbose = verbose
        if proxy and not isinstance(proxy, dict):
            print('Specify the proxy parameters as a dict!', file=sys.stderr)
            sys.exit(1)
            
        """
        Proxy - This is a dict with the following keys
        username, password, host, port
        """
        self.proxy = proxy
        if self.proxy:
            if not self.proxy['host'] or not self.proxy['port']:
                print('Proxy host and port are needed.', file=sys.stderr)
                sys.exit(1)                
            if not self.proxy['username']:
                self.proxy['username'] = ''            
            if not self.proxy['password']:
                self.proxy['password'] = ''
            self.setup_proxy()
            
    def get_ss_params(self, encode=True, **args):
        """
        Method which returns the parameters required for an api call.
        """
        ts = int(time.time())
        tmp_params_dict = {
                        'api_key' : self.params['api_key'],
                        'ts' : ts,
        }
        # Add method specific parameters to the dict.
        for arg in args:
            # Include only params which has non-null value. Otherwise slideshare is getting screwed up!
            if args[arg] and isinstance(args[arg], str) and arg != 'slideshow_srcfile':
                tmp_params_dict[arg]=args[arg]
        
        if not encode:
            return tmp_params_dict
        
        ss_params = urllib.parse.urlencode(tmp_params_dict)
        if self.verbose:
            print('Encoded parameter for this call :', ss_params)
        return ss_params

    def parsexml(self, xml):
        """
        Method which parses the xml returned by slideshare and returns a list of dict.
        Interestingly this is JSON representation of slideshare xml.
        """
        return fromstring(xml)
    
    def make_call(self, service_url, **args):
        """
        Handy method which prepares slideshare parameters accepting extra parameters,
        makes service call and returns JSON output
        """
        params = self.get_ss_params(**args)
        data = urllib.request.urlopen(service_url_dict[service_url]).read()
        json = self.parsexml(data)
        return self.return_data(json)

    def make_auth_call(self, service_url, **args):
        """
        Simillar to make_call, except this does authentication first. Needed for upload
        """
        params = self.get_ss_params(encode=False, **args)
        params['slideshow_srcfile'] = open(args['slideshow_srcfile'], 'rb')        
        opener = urllib.request.build_opener(MultipartPostHandler) # Use our custom post handler which supports unicode
        data = opener.open(service_url_dict[service_url], params).read()
        json = self.parsexml(data)
        return self.return_data(json)
    
    def return_data(self, json):
        """
        Method to trap slideshare error messages and return data if there are no errors
        """
        if json and hasattr(json, 'SlideShareServiceError'):
            print('Slideshare returned the following error - %s' %json.SlideShareServiceError.Message, file=sys.stderr)
            return None
        return json

    def setup_proxy(self):
        if self.proxy:
            if self.verbose:
                print('Using proxy server : ', self.proxy)
            # Urllib2 doesn't support https IMHO. Slideshare thankfully is http
            proxy_support = urllib.request.ProxyHandler({'http': 'http://%(username)s:%(password)s@%(host)s:%(port)s' %self.proxy})
            proxy_opener = urllib.request.build_opener(proxy_support, urllib.request.HTTPHandler)
            urllib.request.install_opener(proxy_opener)

    def download_file(self, fetch_url, save_to=None, **args):
        """
        Method to download a presentation. Supports download via a proxy!
        Requires: url
        Optional: save_to
        """       
        # the path and filename to save your cookies in        
        COOKIEFILE = 'cookies.tmp'
        user_login = args['username']
        user_password = args['password']
        if not user_login or not user_password:
            print('Username and password is needed to download.', file=sys.stderr)
            sys.exit(1)
        login_params = urllib.parse.urlencode( {'user_login' : user_login,
                                          'user_password' : user_password
                                        })
        LOGIN_URL = 'http://www.slideshare.net/login'
        cj = None
        self.do_login_and_fetch(cj, COOKIEFILE, LOGIN_URL, login_params, fetch_url, save_to, **args)
        
    def do_login_and_fetch(self, cj, COOKIEFILE, LOGIN_URL, login_params, fetch_url, save_to, **args):
        """
        Method to do an automated login and save the cookie. This is required for presentation download.
        """
        ClientCookie = None
        cookielib = None
        # Properly import the correct cookie lib 
        try:
            import http.cookiejar
        except ImportError:
            # If importing cookielib fails
            # let's try ClientCookie
            try:
                import ClientCookie
            except ImportError:
                # ClientCookie isn't available either
                urlopen = urllib.request.urlopen
                Request = urllib.request.Request
            else:
                # imported ClientCookie
                urlopen = ClientCookie.urlopen
                Request = ClientCookie.Request
                cj = ClientCookie.LWPCookieJar()        
        else:
            # importing cookielib worked
            urlopen = urllib.request.urlopen
            Request = urllib.request.Request
            cj = http.cookiejar.LWPCookieJar()
        
        if cj is not None:
            if os.path.isfile(COOKIEFILE):
                cj.load(COOKIEFILE)        
            if cookielib is not None:
                opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
                urllib.request.install_opener(opener)        
            else:
                opener = ClientCookie.build_opener(ClientCookie.HTTPCookieProcessor(cj))
                ClientCookie.install_opener(opener)
                
        headers =  {'User-agent' : 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'}
        request = Request(LOGIN_URL, login_params, headers)
        handle = urlopen(request)
        if cj:
            cj.save(COOKIEFILE)        
        request = Request(fetch_url, None, headers)
        try:
            handle = urlopen(request)
        except urllib.error.HTTPError:
            print('Presentation not available for download!', file=sys.stderr)
            return
        data = handle.read()
        info = handle.info()
        ext = 'ppt'
        type = info['Content-Type']
        ext = self.get_extension(type)
        if not save_to:
            save_to = fetch_url.split('/')[-2] + '.'
        save_to = save_to + ext
        fp = open(save_to, 'wb')
        fp.write(data)
        fp.close()
        if self.verbose:
            print('Presentation downloaded and saved to %s' %save_to)
            
    def get_extension(self, type):
        """
        Utility Method to return an extension basend on the content type
        """
        if type in ['application/pdf', 'application/x-pdf']:
            return 'pdf'
        return 'ppt'

    ##############################
    # List of api calls supported by slideshare
    ##############################
    def get_slideshow_by_user(self, username_for=None,offset=None,limit=None):
        """
        Method to get all slideshows created by an user
        Requires: username_for
        Optional: offset, limit
        """
        if not username_for:
            if self.verbose:
                print('No username specified. Using the default : %s' %self.params['username'])
                username_for = self.params['username']
        return self.make_call('slideshow_by_user', username_for=username_for, offset=offset, limit=limit)
        
    def get_slideshow(self, slideshow_id=None):
        """
        Method to retrieve a slideshow, given an id
        Requires: slideshow_id
        """
        if not slideshow_id:
            print('slideshow_id is needed for this call.', file=sys.stderr)
            sys.exit(1)
        return self.make_call('get_slideshow', slideshow_id=str(slideshow_id))
    
    def get_slideshow_by_tag(self, tag=None, offset=None, limit=None):
        """
        Method to retrieve a slideshow by tag
        Requires: tag
        Optional: offset, limit
        """
        if not tag:
            print('A tag is needed for this call.', file=sys.stderr)
            sys.exit(1)
        return self.make_call('slideshow_by_tag', tag=tag, offset=offset, limit=limit)
    
    def upload_slideshow(self, username=None, password=None,
                         slideshow_title=None, slideshow_srcfile=None, slideshow_description=None,
                         slideshow_tags=None, make_src_public='Y', make_slideshow_private='N',
                         generate_secret_url='N', allow_embeds='Y', share_with_contacts='Y'):
        """
        Method to upload a new slideshow. Since slideshare does batch encoding,
        the value returned will be an id. Use get_slideshow to get the exact status
        Requires: username, password, slideshow_title, slideshow_srcfile
        Optional: slideshow_description, slideshow_tags, make_src_public,
make_slideshow_private, generate_secret_url, allow_embeds, share_with_contacts
        """
        if not username or not password or not slideshow_title or not slideshow_srcfile:
            print('Required parameters missing.', file=sys.stderr)
            sys.exit(1)
        if not os.path.exists(slideshow_srcfile):
            print('File to be uploaded missing.', file=sys.stderr)
            sys.exit(1)
            
        return self.make_auth_call('upload_slideshow', username=username, password=password,
                              slideshow_title=slideshow_title, slideshow_srcfile=slideshow_srcfile,
                              slideshow_description=slideshow_description, slideshow_tags=slideshow_tags,
                              make_src_public=make_src_public, make_slideshow_private=make_slideshow_private,
                              generate_secret_url=generate_secret_url, allow_embeds=allow_embeds,
                              share_with_contacts=share_with_contacts)
    
    def delete_slideshow(self, slideshow_id=None):
        """
        Method to delete a slideshow, given an id
        Requires: slideshow_id
        """
        if not slideshow_id:
            print('slideshow_id is needed for this call.', file=sys.stderr)
            sys.exit(1)
        return self.make_call('delete_slideshow', slideshow_id=slideshow_id)
    
    ##############################
    # End of list
    ##############################
    
    ##############################
    # List of api calls not supported by slideshare!
    # Caution: These calls make use of scraping and other means to work.
    ##############################
    def download_slideshow(self, slideshow_id=None, **args):
        """
        Method to download a slideshow, given an id
        Requires: slideshow_id
        """
        download_link = "%(link)s/download"
        if not slideshow_id:
            print('slideshow_id is needed for this call.', file=sys.stderr)
            sys.exit(1)
        json = self.get_slideshow(slideshow_id)
        if not json:
            print('Unable to locate the slideshow', file=sys.stderr)
            return
        if json.Slideshows.Slideshow.Status != '2':
            print('Slideshow not yet available!', file=sys.stderr)
            return
        link = json.Slideshows.Slideshow.Permalink
        download_link = download_link %dict(link=link)
        self.download_file(download_link, **args)
        
    ##############################
    # End of unsupported list
    ##############################

from localsettings import username, password, api_key, secret_key
keys = {'api_key': api_key, 'secret_key': secret_key}
obj = pyslideshare(params_dict=keys)

