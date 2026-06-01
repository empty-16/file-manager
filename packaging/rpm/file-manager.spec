Name:           file-manager
Version:        1.0
Release:        1%{?dist}
Summary:        A Windows 11-style file manager
License:        MIT
BuildArch:      x86_64

%description
A PyQt6-based file manager with a Windows 11 Fluent design.

%install
mkdir -p %{buildroot}/usr/bin
cp -r %{_sourcedir}/file-manager %{buildroot}/usr/bin/

%files
/usr/bin/file-manager

%post
chmod +x /usr/bin/file-manager/file-manager

%changelog
* Mon Jun 01 2026 Empty-16 <yassirboukiri99@gmail.com> - 1.0-1
- Initial RPM release