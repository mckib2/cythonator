
from html.parser import HTMLParser
import re
from lxml import etree as ET

class Typedef:
    def __init__(self, xml):
        assert xml.get('kind') == 'typedef'

        for e in xml.iterchildren():
            if e.tag in set(['type', 'definition', 'argsstring', 'name']):
                setattr(self, e.tag, e.text)

    def __repr__(self):
        out = '%s[%s = %s]' % (self.__class__.__name__, self.name, self.type)
        #for thing in set(vars(self)) - set(['name']):
        #    out += '  %s: %s\n' % (thing, getattr(self, thing))
        return out

class Param:
    def __init__(self, xml):
        assert xml.tag == 'param'

        tipe = list(xml.iterfind('type'))[0]
        if len(list(tipe.iterchildren())):
            # If it has children, it's a refTextType
            h = HTMLParser()
            tipe = h.unescape(ET.tostring(tipe).decode())
            tipe = re.sub(r'<type.*?>', '', tipe)
            tipe = re.sub(r'<ref .*?>', '', tipe)
            tipe = re.sub(r'</ref>', '', tipe)
            tipe = re.sub(r'</type>', '', tipe).strip()
        else:
            tipe = tipe.text

        name = list(xml.iterfind('declname'))
        if len(name):
            self.name = name[0].text
        else:
            self.name = None

        self.raw = tipe

        self.const = 'const' in tipe.split()
        self.ref = '&' in tipe
        self.ptr = '*' in tipe
        self.type = ' '.join(t for t in self.raw.replace('*', '').replace('&', '').split() if t != 'const')

    def __repr__(self):
        out = '%s:\n' % (self.__class__.__name__)
        for thing in vars(self):
            out += '  %s: %s\n' % (thing, getattr(self, thing))
        return out

class Funktion:
    def __init__(self, xml):
        assert xml.get('kind') == 'function'

        self.params = []
        self.templateparamlist = []

        for thing in ['prot', 'static', 'const', 'virt']:
            setattr(self, thing, xml.get(thing))
        self.static = self.static != 'no'
        self.const = self.const != 'no'
        self.virt = self.virt != 'non-virtual'

        for e in xml.iterchildren():
            if e.tag in set(['templateparamlist', 'type', 'definition', 'argsstring', 'name', 'param']):
                if e.tag == 'param':
                    self.params.append(Param(e))
                elif e.tag == 'templateparamlist':
                    for p in e.iterchildren():
                        self.templateparamlist.append(Param(p))
                else:
                    setattr(self, e.tag, e.text)

        self.is_constructor = self.type is None and '~' not in self.name
        self.is_destructor = self.type is None and '~' in self.name

        self.ret_ptr = self.type is not None and '*' in self.type
        self.ret_ref = self.type is not None and '&' in self.type
        self.ret_const = self.type is not None and 'const' in self.type.split()

        # self.namespace = '::'.join(self.definition.split()[-1].split('::')[:-1]) # TODO: needs work
        self.file = next(xml.iterfind('location')).get('file')

        if self.type is None:
            self.ret_type = None
        else:
            self.ret_type = self.type.replace('*', '').replace('&', '').strip()

    def __repr__(self):
        out = '%s[%s]:\n' % (self.__class__.__name__, self.name)
        out += '  params[%d]:\n' % len(self.params)
        for p in self.params:
            pout = str(p)
            for l in pout.strip().split('\n'):
                out += '    %s\n' % l
        out += '  templateparamlist[%d]:\n' % len(self.templateparamlist)
        for p in self.templateparamlist:
            pout = str(p)
            for l in pout.strip().split('\n'):
                out += '    %s\n' % l
        for thing in set(vars(self)) - set(['name', 'params', 'templateparamlist']):
            out += '  %s: %s\n' % (thing, getattr(self, thing))
        return out


class Klass:
    def __init__(self, xml):
        assert xml.get('kind') == 'class'

        self.name = None
        self.functions = []
        self.typedefs = []

        for e in xml.iterchildren():
            if e.tag == 'compoundname':
                self.name = e.text
            elif e.tag == 'sectiondef':
                # Multiple kinds of sectiondef
                if e.get('kind') in set(['public-func', 'public-static-func']):
                    for f in e.iterchildren():
                        self.functions.append(Funktion(f))
                elif e.get('kind') in set(['public-type']):
                    for pt in e.iterchildren():
                        # Multiple kinds of public-type
                        if pt.get('kind') == 'typedef':
                            self.typedefs.append(Typedef(pt))
                else:
                    print(e.get('kind'))


    def __repr__(self):
        out = '%s[%s]:\n' % (self.__class__.__name__, self.name)
        out += '  functions[%d]:\n' % len(self.functions)
        for f in self.functions:
            fout = str(f)
            for l in fout.strip().split('\n'):
                out += '    %s\n' % l
        out += '  typedefs[%d]:\n' % len(self.typedefs)
        for t in self.typedefs:
            tout = str(t)
            for l in tout.strip().split('\n'):
                out += '    %s\n' % l
        return out


def parse(filename='xml/all.xml'):
    tree = ET.parse(filename)

    klasses = []
    typedefs = []
    functions = []

    for e in tree.getroot():
        # First level should be compounddef

        if e.get('kind') == 'class':
            klasses.append(Klass(e))
        elif e.get('kind') == 'namespace':
            for ee in e.iterchildren():
                if ee.tag == 'sectiondef':
                    for md in ee.iterchildren():
                        if md.get('kind') == 'typedef':
                            typedefs.append(Typedef(md))
                        elif md.get('kind') == 'function':
                            functions.append(Funktion(md))
                        else:
                            raise NotImplementedError('Found something new in namespace')
        else:
            print(list(e.iterchildren())[0].text)

    for t in typedefs:
        print(t)
    for f in functions:
        print(f)
    for k in klasses:
        print(k)

    #print(functions[8])

if __name__ == '__main__':
    parse()
