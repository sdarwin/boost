#!/usr/bin/python
#

# Identifies the documentation format of each boost library
# Usage: doc_format.py "path/to/boost"

import os
import sys


def jam_imports_from_dir(dir_path):
    jam_path = None
    imports = []
    for jam_basename in ['Jamfile.v2', 'Jamfile', 'Jamfile.jam', 'jamfile.jam', 'jamfile.v2', 'jamfile', 'build.jam']:
        if os.path.exists(os.path.join(dir_path, jam_basename)):
            jam_path = os.path.join(dir_path, jam_basename)
            break
    if jam_path:
        imports = []
        used_boostbook = False
        with open(jam_path, 'r') as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 3 and parts[0] in ['import', 'using'] and parts[2] in [';', ':']:
                    # filter modules unrelated to docs
                    module = parts[1]
                    if module not in ['notfile', 'path', 'set', 'os', 'regex', 'modules', 'testing', 'common',
                                      'project', 'boostrelease', 'type', 'generators', 'snippet-extractor', 'sequence',
                                      'print']:
                        if module.endswith('.jam'):
                            module = os.path.basename(module)[:-4]
                        if module != 'toolset':
                            imports.append(module)
                        else:
                            imports.append('boostbook')
                            imports.append('doxygen')
                if len(parts) > 2 and parts[0].strip() == 'actions' and parts[1] == 'sphinx-build':
                    imports.append('sphinx')
                elif len(parts) > 2 and parts[0].strip() == 'sphinx-build' and parts[1] == '-b':
                    imports.append('sphinx')
                if len(parts) >= 2 and parts[0].strip() == 'boostbook':
                    used_boostbook = True
        if len(imports) > 1 and 'boostdoc' in imports:
            imports.remove('boostdoc')
        if len(imports) == 0 and used_boostbook:
            imports.append('boostbook')

        # remove redundant entries when one tool implies the other
        def try_remove(ls, e):
            if e in ls:
                ls.remove(e)

        imports = list(set(imports))
        try_remove(imports, 'doxygen')
        if 'docca' in imports:
            imports.append('quickbook')
            imports.remove('docca')

        if 'quickbook' in imports:
            try_remove(imports, 'doxygen')
            try_remove(imports, 'boostbook')
            try_remove(imports, 'auto-index')
            try_remove(imports, 'docca')
            try_remove(imports, 'xsltproc')
            try_remove(imports, 'docutils')

    return imports


def is_jamfile(file_path):
    return os.path.basename(file_path) in ['Jamfile.v2', 'Jamfile', 'jamfile.v2', 'jamfile', 'build.jam']


def is_image_file(file_path):
    return any(file_path.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg'])


def is_source_file(file_path):
    return any(file_path.endswith(ext) for ext in ['.cpp', '.hpp', '.sh', '.bat', '.py', '.pl'])


def is_pure_html_doc_file(file_path, message=False):
    if os.path.exists(file_path) and os.path.isdir(file_path):
        return False
    v = any(
        file_path.endswith(ext) for ext in
        ['.html', '.htm', '.css', '.js', '.txt', '.reno', '.pdf', '.dot', '.w', '.rst', '.sty', '.fig', '.graffle',
         'readme', '.chs', '.tcl', '.md', '.csh', 'HEAD', 'Makefile', '.xml', 'Doxyfile.in']) or \
        is_image_file(file_path) or \
        is_jamfile(file_path) or is_source_file(file_path)
    if not v and message:
        print(f'{file_path} not an html doc file')
    return v


def is_pure_html_doc_dir(dir_path):
    if not os.path.exists(dir_path):
        return False
    if not os.path.isdir(dir_path):
        return False
    return all(
        os.path.basename(dir_path) == '.git' or
        is_pure_html_doc_dir(os.path.join(dir_path, f)) or
        is_pure_html_doc_file(os.path.join(dir_path, f), True) for f in os.listdir(dir_path) if
        os.path.isfile(os.path.join(dir_path, f))) and any(
        [f.endswith('.html') or f.endswith('.htm') for f in os.listdir(dir_path)])


def contains_pure_html_dir(dir_path):
    if not os.path.exists(dir_path):
        return False
    if not os.path.isdir(dir_path):
        return False
    return any(f.endswith('.html') or f.endswith('.htm') for f in os.listdir(dir_path))


def has_cpp_files(dir_path):
    """
    Recursively searches for .cpp files in a directory.
    Returns True if at least one .cpp file is found, False otherwise.
    """
    for root, dirs, files in os.walk(dir_path):
        for file in files:
            if file.endswith('.cpp'):
                return True
    return False


def main(src_root):
    # Library doc dirs
    custom_doc_dirs = {
        'functional': ['factory/doc', 'forward/doc', 'overloaded_function/doc'],
        'numeric': ['conversion/doc', 'odeint/doc', 'interval/doc', 'ublas/doc']
    }

    def doc_dirs(lib_name):
        if lib_name in custom_doc_dirs:
            return custom_doc_dirs[lib_name]
        return ['doc', 'xmldoc', 'doc/xml']

    # Identify jamfile imports
    libdoc_imports = {}
    libs_dir = os.path.join(src_root, 'libs')
    tools_dir = os.path.join(src_root, 'tools')
    for main_dir in [libs_dir, tools_dir]:
        for lib in os.listdir(main_dir):
            lib_path = os.path.join(main_dir, lib)
            if os.path.isdir(lib_path):
                rel_path = os.path.relpath(lib_path, src_root)
                libdoc_imports[rel_path] = []
                for doc_pathname in doc_dirs(lib):
                    lib_docs_path = os.path.join(lib_path, doc_pathname)
                    if os.path.isdir(lib_path):
                        libdoc_imports[rel_path] += jam_imports_from_dir(lib_docs_path)
                        libdoc_imports[rel_path] = list(set(libdoc_imports[rel_path]))

    # Accumulate the documentation categories
    libdoc_imports = dict(sorted(libdoc_imports.items()))
    doc_categories = {}
    for [lib, imports] in libdoc_imports.items():
        if imports:
            category = "+".join(imports)
        else:
            lib_path = os.path.join(src_root, lib)
            doc_path = os.path.join(lib_path, 'doc')
            if is_pure_html_doc_dir(doc_path) or contains_pure_html_dir(lib_path):
                category = "HTML"
            elif os.path.exists(os.path.join(lib_path, 'README.md')):
                category = "README.md"
            else:
                category = "No docs"
        if category is None:
            continue
        if category not in doc_categories:
            doc_categories[category] = []
        doc_categories[category].append(os.path.basename(lib))

    # Print report
    doc_categories = dict(sorted(doc_categories.items(), key=lambda x: len(x[1]), reverse=True))
    for [cat, libs] in doc_categories.items():
        print(f'{cat} ({len(libs)}): {libs}')

    # Check which libraries have source files
    print('Compiled libraries:')
    for lib in libdoc_imports:
        lib_path = os.path.join(src_root, lib)
        lib_src_path = os.path.join(lib_path, 'src')
        has_cpp = False
        if os.path.exists(lib_src_path) and os.path.isdir(lib_src_path):
            has_cpp = has_cpp_files(lib_src_path)
        lib_include_path = os.path.join(lib_path, 'include')
        if not has_cpp and os.path.exists(lib_include_path) and os.path.isdir(lib_include_path):
            has_cpp = has_cpp_files(lib_include_path)
        if has_cpp:
            print(f'- {os.path.basename(lib)}')

    return 0


if __name__ == "__main__":
    main(os.getcwd() if len(sys.argv) == 1 else sys.argv[1])
