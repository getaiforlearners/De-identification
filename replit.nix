{pkgs}: {
  deps = [
    pkgs.glibcLocales
    pkgs.unixODBC
    pkgs.postgresql
    pkgs.openssl
  ];
}
