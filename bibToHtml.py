import copy
import sys
from datetime import date
import re

def cleanup_title(s):
    s = s.lower()
    s = s.capitalize()
    return s

def cleanup_page(s):
    s = s.replace('--', '-')
    return s

def convert_umlaute_to_html(text):
    umlaute_mapping = {
        r'{\\\"{u}}': '&uuml;',
        r'{\\\"{U}}': '&Uuml;',
        r'{\\\"{a}}': '&auml;',
        r'{\\\"{A}}': '&Auml;',
        r'{\\\"{o}}': '&ouml;',
        r'{\\\"{O}}': '&Ouml;',
        r'{\\\'{a}}': '&aacute;',
        r'{\\\'{A}}': '&Aacute;',
        r'{\\\'{e}}': '&eacute;',
        r'{\\\'{E}}': '&Eacute;',
        r'{\\\'{o}}': '&oacute;',
        r'{\\\'{O}}': '&Oacute;',
        r'{\\\'{u}}': '&uacute;',
        r'{\\\'{U}}': '&Uacute;',
        r'{\\\'{y}}': '&yacute;',
        r'{\\\'{Y}}': '&Yacute;',
        r'{\\\^\'{\}}': '&circ;',
        r'{\\`{a}}': '&agrave;'
    }

    for umlaut, html_entity in umlaute_mapping.items():
        text = re.sub(umlaut, html_entity, text)

    return text

def remove_braces_around_short_text(input_text):
    pattern = r'\{([^{}\d]{1,7})\}'
    return re.sub(pattern, r'\1', input_text)

# Get the BibTeX, template, and output file names
if len(sys.argv) < 3:
    sys.exit("Error: Invalid command.")
else:
    bibfile = sys.argv[1]
    templatefile = sys.argv[2]
    if len(sys.argv) == 4:
        print_to_stdout = 0
        outputfile = sys.argv[3]
    elif len(sys.argv) == 3:
        print_to_stdout = 1

# Open, read, edit and close the BibTeX and template files
with open(bibfile, 'r') as file:
    text = file.read()
    text = text.replace(' and', ',')
    text = text.replace('{-}', '-')
    text = text.replace(r"{\'{\i}}", '&iacute;')
    text = text.replace('{\&}', '&amp')
    converted_text1 = convert_umlaute_to_html(str(text))
    converted_text2 = remove_braces_around_short_text(str(converted_text1))

with open('edit.bib', 'w')  as file:
    file.write(converted_text2)

with open(templatefile, 'r') as f:
    template = f.read()

with open('edit.bib', 'r') as f:
    datalist = f.readlines()

# Discard unwanted characteres and commented lines
datalist = [s.strip('\n\t') for s in datalist]
datalist = [s for s in datalist if s[:2] != '%%']

# Convert a list into a string
data = ''
for s in datalist: data += s

# Split the data at the separators @article, @inproceedings, @incollection, @proceedings
split_pattern = r"@article|@inproceedings|@incollection|@proceedings"
biblist = re.split(split_pattern, data)
# Discard empty strings from the list
biblist = [s.strip() for s in biblist if s.strip() != '']
print(biblist)

# Create a list of lists containing the strings "key = value" of each bibitem
listlist = []
for s in biblist:
    type, sep, s = s.partition('{')
    id, sep, s = s.partition(',')
    s = s.rpartition('}')[0]
    keylist = ['type = ' + type.lower(), 'id = ' + id]
    number = 0
    flag = 0
    i = 0
    separator = 'empty'
    while len(s) > 0:
        if number == 0 and separator == 'empty' and s[i] == '{':
            number += 1
            flag = 1
            separator = 'bracket'
        elif number == 0 and separator == 'empty' and s[i] == '"':
            number += 1
            flag = 1
            separator = 'quote'
        elif number == 1 and separator == 'bracket' and s[i] == '}':
            number -= 1
        elif number == 1 and separator == 'quote' and s[i] == '"':
            number -= 1

        if number == 0 and flag == 1:
            keylist.append(s[:i + 1])
            s = s[i + 1:]
            flag = 0
            i = 0
            separator = 'empty'
            continue

        i += 1

    keylist = [t.strip(' ,\t\n') for t in keylist]
    listlist.append(keylist)

# Create a list of dicts containing key : value of each bibitem
dictlist = []
for l in listlist:
    keydict = {}
    for s in l:
        key, sep, value = s.partition('=')
        key = key.strip(' ,\n\t{}')
        key = key.lower()
        value = value.strip(' ,\n\t{}"')
        keydict[key] = value

    dictlist.append(keydict)

# Backup all the original data
dictlist_bkp = copy.deepcopy(dictlist)

# Lower case of all keys in dictionaries
dictlist = []
for d in dictlist_bkp:
    dlower = {k: v for (k, v) in d.items()}
    dictlist.append(dlower)

dictlist = [d for d in dictlist if 'title' in d]
dictlist = [d for d in dictlist if d['title'] != '']

# Get a list of the article years and the min and max values
years = [int(d['year']) for d in dictlist if 'year' in d]
years.sort()
older = years[0]
newer = years[-1]

# Set the fields to be exported to html (following this order)
mandatory = ['author', 'title']
optional = ['journal', 'eprint', 'volume', 'pages', 'booktitle', 'year', 'url', 'doi', 'editor']

# Clean up data
for i in range(len(dictlist)):
    dictlist[i]['title'] = cleanup_title(dictlist[i]['title'])

# Write down the list html code
counter = 0
html = ''
for y in reversed(range(older, newer + 1)):
    if y in years:
        html += '<h3 id="y{0}">{0}</h3>\n\n\n<ul>\n'.format(y)
        for d in dictlist:
            if 'year' in d and int(d['year']) == y:
                mandata = [d[key] if key in d else 'Unknown' for key in mandatory]# Use 'Unknown' if author is missing
                if 'editor' in d:
                    mandata[0] = d['editor'] # Use editor if author is missing and editor is available
                html += '<li>{0}, <i>{1}</i>'.format(*mandata)

                for t in optional:
                    if t in d:
                        if t == 'journal': html += ', {0}'.format(d[t])
                        if t == 'eprint': html += ':{0}'.format(d[t])
                        if t == 'volume': html += ' <b>{0}</b>'.format(d[t])
                        if t == 'pages':
                            a = cleanup_page(d[t])
                            html += ', {0}'.format(a)
                        if t == 'year': html += ', {0}'.format(d[t])
                        if t == 'url':
                            html += ' <a href="{0}">[link]</a>'.format(d[t])
                html += '</li>\n'
                counter += 1

        html += '</ul>\n'

# Fill up the empty fields in the template
a, mark, b = template.partition('<!--LIST_OF_REFERENCES-->')
a = a.replace('<!--NUMBER_OF_REFERENCES-->', str(counter), 1)
a = a.replace('<!--NEWER-->', str(newer), 1)
a = a.replace('<!--OLDER-->', str(older), 1)
now = date.today()
a = a.replace('<!--DATE-->', date.today().strftime('%d %b %Y'))

# Join the header, list and footer html code
final = a + html + b

# Write the final result to the output file or to stdout
if print_to_stdout == 0:
    with open(outputfile, 'w') as f:
        f.write(final)
else:
    print(final)
