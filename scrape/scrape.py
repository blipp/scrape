#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 02.02.2013

@author: mova
'''
##################License#############
#Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
##########################################

#import hashlib
import urllib2, base64
import os
import re
import urlparse
import __future__
import BeautifulSoup as bs #import bs4 as bs
#import smtplib
#from email.MIMEText import MIMEText
#from email.utils import TICK
import mechanize
import keyring
from glob import glob
from urlparse import urljoin


if not os.path.exists('/dev/shm/tmp'):
    os.system("mkdir /dev/shm/tmp")
if not os.path.exists('/tmp/ram'):
    os.system("ln -s /dev/shm/tmp/ /tmp/ram")

###Edit this
user = ""

def run_script(script, stdin=None):
    """Returns (stdout, stderr), raises error on non-zero return code"""
    import subprocess
    # Note: by using a list here (['bash', ...]) you avoid quoting issues, as the 
    # arguments are passed in exactly this order (spaces, quotes, and newlines won't
    # cause problems):
    proc = subprocess.Popen(['bash', '-c', script],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        stdin=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    if proc.returncode:
        raise ScriptException(proc.returncode, stdout, stderr, script)
    return stdout, stderr

class ScriptException(Exception):
    def __init__(self, returncode, stdout, stderr, script):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        Exception.__init__('Error in script')

def sendmessage(to, subject, content):
    msg = MIMEText(("Hallo "+to+"\n").encode('utf-8'), _charset='utf-8')
    msg['Subject'] = subject
    msg['From'] = "Ultimate Script"
    msg['To'] = to
    s = smtplib.SMTP('localhost')
    s.sendmail(user+"@nowhere.invalid.com", to, msg.as_string())
    s.quit()

def w3m_output(htmltext):
    filepath = "/tmp/ram/w3m.htm"
    run_script("w3m -dump -T text/html << eof > " + filepath + "\n" + htmltext + "\neof\n")
    run_script("w3m -dump -T text/html << eof \n" + htmltext + "\neof\n")
    f = open(filepath, 'r')
    text = f.read()
    f.close()
    return text

def pretty_title(title):
    title = title.title()
    title = re.sub(r"\s+", '_', title)
    if len(re.findall(r"\d+",title))>0:
        number = re.findall(r"\d+",  title)[-1]
        title = re.sub(r"\d+", "", title)
        title = number+"-"+title
    title = re.sub(r"Pdf", 'pdf', title, re.I)
    title = re.sub(r"_\.pdf$", '.pdf', title)
    return title

def get_ilias_url(br, url):
    return br.open(url).read()
def get_ilias_onlinelist(br, url, regex):
    data = br.open(url).read()
    htmlinkl = {}
    htm = bs.BeautifulSOAP(data)
    if len(htm.findAll("a", { "class" : "il_ContainerItemTitle"})) > 0:
        for e in (bs.BeautifulSOAP(data)).findAll("a", { "class" : "il_ContainerItemTitle"}):
            htmlinkl.update({pretty_title(e.getText()+".pdf" ): e["href"]})
    foo = htmlinkl
    for l in htmlinkl:
        htmlinkl.update({l : str(urlparse.urljoin(url, htmlinkl[l]))})
    return htmlinkl


def syncfolders_ilias(br, folder, url, onlinelist):
    if not os.path.isdir(folder):
        raise Exception("No folder"+ folder)
    newfiles = str()
    for x in onlinelist:
        filepath = folder + x
        if not os.path.isfile(filepath):
            doc = get_ilias_url(br, onlinelist[x])
            if  not isinstance(doc, type(None)):
                savefile =open( filepath , "wb")
                savefile.write(doc)
                savefile.close()
                print( "[++] " + filepath)
                newfiles = newfiles + filepath  +"\n"
    print "[e-] " + folder + " completed"
    return newfiles

class ilias_browser(mechanize.Browser):
    """creater a Browser, logs in in Ilias and gives it back"""
    def __init__(self, factory=mechanize.RobustFactory(), history=None, request_class=None):
        mechanize.Browser.__init__(self, factory, history, request_class)
        br = self
        
        if len(keyring.get_password('ilias', user)):
            keyring.set_password('ilias', user,'password')
        

        br.set_handle_robots(False)
        br.set_handle_equiv(True)
        br.set_handle_redirect(True)
        br.set_handle_referer(True)
        br.open('https://ilias.studium.kit.edu/login.php?target=&client_id=produktiv&cmd=force_login&lang=de')
        br.select_form(name="formlogin")
        control = br.find_control(name="idp_selection")
        control.items[1].selected=True
        br.submit()
        br.select_form(nr=0)
        br["j_username"] = user
        br["j_password"] = keyring.get_password('ilias', user)
        br.submit()
        br.select_form(nr=0)
        br.submit()
        br.select_form(nr=0)
        br.submit()
        br.select_form(nr=0)
        br.submit()
    def get_url(self, url):
        br = self
        resp = br.open(url)
        return str(resp.read())




def get_url(url):
    req = urllib2.Request(url)
    try:
        res = urllib2.urlopen(req)
        data = res.read()
        return data
    except IOError, e:
        if hasattr(e, 'code'):
            if e.code != 401:
                err = "%s ERROR(%s)" % (url,e.code)
                print err
            #401 = auth required error
            elif e.code == 401:
                base64string = base64.encodestring('%s:%s' % ("user", "password")).replace('\n', '')
                req.add_header("Authorization", "Basic %s" % base64string)
                try:
                    res = urllib2.urlopen(req)
                    #headers = res.info().headers
                    data = res.read()
                    return data
                except IOError, e:
                        if hasattr(e, 'reason'):
                            #foo  foo
                            foo = "fooo"
                            err = "%s:%s@%s ERROR(%s)" % (foo["user"],foo["pass"],foo["url"],e.reason)
                            print err
                        elif hasattr(e, 'code'):
                            err = "%s:%s@%s ERROR(%s)" % (foo["user"],foo["pass"],foo["url"],e.code)
                            print err
            else:
                err = "%s query complete" % (url)
                print err

def get_onlinelist(url, regex):
    data = get_url(url)
    htmlinkl = {}
    for e in (bs.BeautifulSOAP(data)).findChildren("a", href=re.compile(regex)):
        if  re.findall(r"(\d+)", e["href"],re.I):
            link = urlparse.urljoin(url, e["href"])
            name = (link.split("/")[-1])
            htmlinkl.update({pretty_title(name) : link})
    return htmlinkl

def syncfolders(folder, url, onlinelist):
    if not os.path.isdir(folder):
        raise Exception("No folder"+ folder)
    newfiles = str()
    for x in onlinelist:
        splitted = (onlinelist[x]).split("/")[-1]
        filepath = folder + splitted
        if not os.path.isfile(filepath):
            doc = get_url(onlinelist[x])
            if  not isinstance(doc, type(None)):
                savefile =open( filepath , "wb")
                savefile.write(doc)
                savefile.close()
                print( "[++] " + filepath)
                newfiles = newfiles + filepath  +"\n"
    print "[e-] " + folder + " completed"
    return newfiles


def normdir(folder, url, regex):
    print "[s+] " + folder + " started"
    onlinelist = get_onlinelist(url, regex)
    return syncfolders(folder, url, onlinelist)
def iliasdir(folder, url, regex):
    print "[s+] " + folder + " started"
    br = ilias_browser()
    onlinelist = get_ilias_onlinelist(br, url, '.*')    
    for n in xrange(1,2):
        if len(onlinelist)<1:
            print "Failed fetching!\n Next try (" + str(n+1) + "/3)"
            print onlinelist
            br = ilias_browser()
            onlinelist = get_ilias_onlinelist(br, url, '.*')
    return syncfolders_ilias(br, folder, url, onlinelist)

if __name__ == '__main__':
    print """Scraping Script. MIT-License. NO WARRANTY."""
    newfiles = ""
    stack = {
    "1" : { "folder":u"", "url":"", "regex":'.*', "ilias":True, "list":True},
    "2" : { "folder":u"", "url":"", "regex":'.*', "ilias":False, "list":True},
    }

    for subject in stack:
        if not stack[subject]["list"]:
            if stack[subject]["ilias"]:
                iliasdir(stack[subject]["folder"],stack[subject]["url"],stack[subject]["regex"])
            else:
                normdir(stack[subject]["folder"],stack[subject]["url"],stack[subject]["regex"])
        else:
            if stack[subject]["ilias"]:
                newfiles = newfiles + iliasdir(stack[subject]["folder"],stack[subject]["url"],stack[subject]["regex"])
            else:
                newfiles = newfiles + normdir(stack[subject]["folder"],stack[subject]["url"],stack[subject]["regex"])
    f = open(os.path.expanduser('~')+"/to_print.txt", "w")
    f.write(newfiles.encode('utf8'))
    f.close()
