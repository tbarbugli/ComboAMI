import gzip
import re
import shlex
import StringIO
import sys
import time
import urllib2

from email.parser import Parser
from argparse import ArgumentParser


def comboami_version():
    return "2.6.1"


def comboami_defaultbranch():
    return "2.6"


def curl_instance_data(url):
    for i in range(20):
        try:
            req = urllib2.Request(url)
            return req
        except urllib2.HTTPError:
            time.sleep(5)
    sys.exit('Couldn\'t curl instance data after 60 seconds')


def read_instance_data(req):
    data = urllib2.urlopen(req).read()
    try:
        stream = StringIO.StringIO(data)
        gzipper = gzip.GzipFile(fileobj=stream)
        return gzipper.read()
    except IOError:
        stream = StringIO.StringIO(data)
        return stream.read()


def is_multipart_mime(data):
    match = re.search('Content-Type: multipart', data)
    if match:
        return True


def get_user_data(req):
    data = read_instance_data(req)
    if is_multipart_mime(data):
        message = Parser().parsestr(data)
        for part in message.walk():
            if (part.get_content_type() == 'text/plaintext'):
                match = re.search('totalnodes', part.get_payload())
                if (match):
                    return part.get_payload()
    else:
        return data


def get_ec2_data():
    instance_data = {}
    # Try to get EC2 User Data
    try:
        req = curl_instance_data('http://169.254.169.254/latest/user-data/')
        instance_data['userdata'] = get_user_data(req)
    except Exception, e:
        instance_data['userdata'] = ''

    return instance_data


def parse_ec2_userdata():
    instance_data = get_ec2_data()

    # Setup parser
    parser = ArgumentParser()

    # Development options
    # Option that specifies repository to use for updating
    parser.add_argument("--repository", action="store", type=str, dest="repository")
    # Option that specifies the commit to use for updating (instead of the latest) -- kept for backwards compatibility
    parser.add_argument("--forcecommit", action="store", type=str, dest="forcecommit")

    try:
        (args, unknown) = parser.parse_known_args(shlex.split(instance_data['userdata']))
        return args
    except:
        return None


def repository():
    options = parse_ec2_userdata()

    repository = None
    commitish = ''

    if options:
        # Backwards compatibility: If --forcecommit was used, always use the
        # official repository.
        if options.forcecommit:
            commitish = options.forcecommit
        elif options.repository:
            parts = options.repository.split('#')
            nparts = len(parts)
            if nparts > 0:
                repository = parts[0]
                if nparts > 1:
                    commitish = parts[1]
        else:
            repository = 'https://github.com/riptano/ComboAMI#%s' % comboami_defaultbranch()

    return (repository, commitish)
