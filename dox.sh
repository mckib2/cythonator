
# Process the header files
touch Doxyfile
echo "QUIET = YES" >> Doxyfile
echo "GENERATE_XML = YES" >> Doxyfile
echo "GENERATE_HTML = NO" >> Doxyfile
echo "GENERATE_LATEX = NO" >> Doxyfile
echo "XML_PROGRAMLISTING = NO" >> Doxyfile
#echo "XML_NS_MEMB_FILE_SCOPE = YES" >> Doxyfile
echo "EXTRACT_ALL = YES" >> Doxyfile
echo "INPUT = $@" >> Doxyfile
doxygen Doxyfile
rm Doxyfile

# Combine the XML files
(cd xml && xsltproc combine.xslt index.xml > all.xml)

# Parse the XML
python parse_xml.py
