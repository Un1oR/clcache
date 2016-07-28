from __future__ import print_function

import argparse
import glob
import os
import sys
import textwrap
import subprocess


def ensure_dir(path):
    if os.path.exists(path):
        return
    
    os.mkdir(path)
    return path


def traverse_toolsets(f):
    msbuild_dir = r'C:\Program Files (x86)\MSBuild'
    toolsets = glob.glob(r'{}\Microsoft.Cpp\v4.0\*\Platforms\*\PlatformToolsets\*'.format(msbuild_dir))
    for toolset in toolsets:
        f(toolset)


def clcache_props_path(toolset):
    return os.path.join(toolset, 'ImportAfter', 'Clcache.props')


def generate_props_content(clcache_dir):
    return textwrap.dedent('''
        <Project xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
          <PropertyGroup>
            <ExecutablePath>{clcache_dir};$(ExecutablePath)</ExecutablePath>
          </PropertyGroup>
        </Project>''').format(clcache_dir=clcache_dir)[1:]


def check_call_quiet(*args, **kwargs):
    with open(os.devnull, 'w') as devnull:
        kwargs['stderr'] = devnull
        kwargs['stdout'] = devnull
        subprocess.check_call(*args, **kwargs)


def set_system_variable(var, value):
    if value:
        check_call_quiet(['setx', '-m', var, value])
    else:
        reg_path = r'HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment'
        try:
            check_call_quiet(['reg', 'query', reg_path, '/V', var])
        except subprocess.CalledProcessError:
            # Variable doesn't exists
            pass
        else:
            check_call_quiet(['reg', 'delete', reg_path, '/F', '/V', var])
    
        
def install(exe, cache_dir):
    def f(toolset):
        clcache_props = clcache_props_path(toolset)
        ensure_dir(os.path.dirname(clcache_props))
        with open(clcache_props, 'w') as f:
            f.write(generate_props_content(os.path.dirname(exe)))
    
    traverse_toolsets(f)
    set_system_variable('CLCACHE_DIR', cache_dir)
    set_system_variable('CL', '/MP4')


def uninstall():
    def f(toolset):
        clcache_props = clcache_props_path(toolset)
        if os.path.exists(clcache_props):
            os.remove(clcache_props)

    traverse_toolsets(f)
    set_system_variable('CLCACHE_DIR', None)
    set_system_variable('CL', None)


def main(args=sys.argv[1:]):
    clcache_default_exe = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'dist',
        'cl.exe')
    
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='action')
    parser_install = subparsers.add_parser('install')
    parser_install.add_argument('--exe', default=clcache_default_exe)
    parser_install.add_argument('--cache-dir')
    parser_uninstall = subparsers.add_parser('uninstall')
    args = parser.parse_args(args)

    if args.action == 'install':
        install(args.exe, args.cache_dir)
    else:
        uninstall()


if __name__ == '__main__':
    sys.exit(main())