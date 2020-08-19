'''Generate Header files for tests using templates.'''

from collections import namedtuple
import pathlib

from jinja2 import Environment, FileSystemLoader

Type = namedtuple('Type', 'name tag_safe')

# C types
C_MAIN_TYPES = [Type(name=t, tag_safe='_'.join(t.split(' '))) for t in [
    'void',
    'char',
    'signed char',
    'unsigned char',
    'short', 'short int', 'signed short', 'signed short int',
    'unsigned short', 'unsigned short int',
    'int', 'signed', 'signed int',
    'unsigned', 'unsigned int',
    'long', 'long int', 'signed long', 'signed long int',
    'unsigned long', 'unsigned long int',
    'long long', 'long long int', 'signed long long', 'signed long long int',
    'unsigned long long', 'unsigned long long int',
    'float',
    'double',
    'long double',
]]
C_COMPLEX_TYPES = [Type(name=t, tag_safe='_'.join(t.split(' '))) for t in [
    'float _Complex',
    'double _Complex', 'long double _Complex',
]]
C_BOOLEAN_TYPES = [Type(name=t, tag_safe='_'.join(t.split(' '))) for t in [
    '_Bool',
    'bool',
]]


def generate_test_headers():

    # All the types we want to test
    TYPES = C_MAIN_TYPES + C_COMPLEX_TYPES + C_BOOLEAN_TYPES
    ARGTYPES = C_MAIN_TYPES

    # Load templates
    func_template = 'functions.jinja'
    file_loader = FileSystemLoader('tests/templates')
    env = Environment(loader=file_loader)
    template = env.get_template(func_template)
    output = template.render(TYPES=TYPES, ARGTYPES=ARGTYPES)

    pathlib.Path('tests/headers/').mkdir(exist_ok=True)
    with open('tests/headers/%s.hpp' % pathlib.Path(func_template).name, 'w') as fp:
        fp.write('#include <cstdbool>\n')
        fp.write(output)


if __name__ == '__main__':
    generate_test_headers()
