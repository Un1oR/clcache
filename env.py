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


def generate_props_content(exe):
    return textwrap.dedent('''
        <Project xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
          <PropertyGroup>
            <ClToolExe>{exe}</ClToolExe>
            <ClToolPath>{dir}</ClToolPath>
          </PropertyGroup>
        </Project>''').format(
            exe=os.path.basename(exe),
            dir=os.path.dirname(exe))[1:]


def check_call_quiet(*args, **kwargs):
    with open(os.devnull, 'w') as devnull:
        kwargs['stderr'] = devnull
        kwargs['stdout'] = devnull
        subprocess.check_call(*args, **kwargs)


def set_system_variable(var, value):
    if value:
        check_call_quiet(['setx', var, value])
    else:
        reg_path = r'HKEY_CURRENT_USER\Environment'
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
            f.write(generate_props_content(exe))
    
    traverse_toolsets(f)
    set_system_variable('CLCACHE_DIR', cache_dir)


def uninstall():
    def f(toolset):
        clcache_props = clcache_props_path(toolset)
        if os.path.exists(clcache_props):
            os.remove(clcache_props)

    traverse_toolsets(f)
    set_system_variable('CLCACHE_DIR', None)


def main(args=sys.argv[1:]):
    clcache_default_exe = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'dist',
        'clcache.exe')

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='action')
    parser_install = subparsers.add_parser('install')
    parser_install.add_argument('--exe', type=argparse.FileType('r'), default=clcache_default_exe)
    parser_install.add_argument('--cache-dir')
    parser_uninstall = subparsers.add_parser('uninstall')
    args = parser.parse_args(args)

    if args.action == 'install':
        exe = os.path.abspath(args.exe.name)
        cache_dir = os.path.abspath(args.cache_dir) if args.cache_dir else None
        install(exe, cache_dir)
    else:
        uninstall()


if __name__ == '__main__':
    sys.exit(main())