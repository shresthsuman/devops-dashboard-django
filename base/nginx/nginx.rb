require 'erb'
require 'yaml'

# read config
nginx = YAML.load_file('services.yml')

# template vars from configuration with fallback values
@hostname = nginx['services']['hostname'] || '_'
@paths    = nginx['services']['paths']    || []
@ports    = nginx['services']['ports']    || [80]

# vhost template
template = "server {
  server_name  <%= @hostname %>;

  <% @ports.each do |port| %>
  listen <%= port %>;
  <% end %>

  ssl_certificate /etc/ssl/wildcard.testing.mms-at-work.de.pem;
  ssl_trusted_certificate /etc/ssl/wildcard.testing.mms-at-work.de.pem;
  ssl_certificate_key /etc/ssl/wildcard.testing.mms-at-work.de.pem;
  ssl_protocols TLSv1 TLSv1.1 TLSv1.2;
  ssl_prefer_server_ciphers on;

  ssl_ciphers 'ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-DSS-AES128-GCM-SHA256:kEDH+AESGCM:ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES256-SHA384:ECDHE-ECDSA-AES256-SHA384:ECDHE-RSA-AES256-SHA:ECDHE-ECDSA-AES256-SHA:DHE-RSA-AES128-SHA256:DHE-RSA-AES128-SHA:DHE-DSS-AES128-SHA256:DHE-RSA-AES256-SHA256:DHE-DSS-AES256-SHA:DHE-RSA-AES256-SHA:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:AES256-SHA256:AES128-SHA:AES256-SHA:AES:CAMELLIA:DES-CBC3-SHA:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!MD5:!PSK:!aECDH:!EDH-DSS-DES-CBC3-SHA:!EDH-RSA-DES-CBC3-SHA:!KRB5-DES-CBC3-SHA';
  ssl_session_timeout 1d;
  ssl_session_cache shared:SSL:50m;
  ssl_stapling on;
  ssl_stapling_verify on;


  <% @paths.each do |path | %>
  location <%= path['path'] %> {
    include proxy.conf;
    set $<%= path['backend']['serviceName'] %> <%= path['backend']['serviceName'] %>;
    proxy_pass http://<%= path['backend']['serviceName'] %>:<%= path['backend']['servicePort'] %><%= path['backend']['servicePath'] || '/' %>;
  }
  <% end %>
}"

# create the config file
File.open('vhost.conf', 'w') do |f|
  f.write ERB.new(template).result( binding )
end
