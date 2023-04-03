{ pkgs, config, ... }:

{
  time.timeZone = "Europe/Warsaw";
  networking.useDHCP = false;
  networking.hostName = "oioioi";
  networking.domain = "local";

  services.filetracker = {
    enable = true;
  };

  services.filetracker-cache-cleaner = {
    enable = true;
    sizeLimit = "10G";
  };

  networking.firewall.allowedTCPPorts = [ 80 ];

  # Allow local users to access the database.
  services.postgresql.authentication = ''
    # TYPE  DATABASE    USER        CIDR-ADDRESS          METHOD
    local   all         sio2                               trust
  '';

  services.sioworker = {
    enable = true;
    memoryLimit = 2048;
  };

  # For ssl stapling
  #services.nginx.resolver.addresses = [ "1.1.1.1" ];
  #services.nginx.recommendedTlsSettings = true;

  services.oioioi = {
    enable = true;
    #domain = "example.com";
    #useSSL = true;
    nginx = {
      #sslCertificateKey = "/foo.key" ;
      #sslCertificate = "/foo.pem";
    };
  };

  environment.systemPackages = with pkgs; [
    htop
    # For the `filetracker` CLI
    filetracker
    python3
  ];
}
