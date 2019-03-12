FROM ruby:2.4-alpine as config

COPY ./nginx/nginx.rb /tmp/nginx.rb
COPY ./nginx/services.yml /tmp/services.yml

WORKDIR /tmp

RUN ruby nginx.rb

FROM nginx:stable-alpine

EXPOSE 80 443

COPY ./certificates/wildcard.testing.mms-at-work.de.pem /etc/ssl/
COPY ./nginx/proxy.conf /etc/nginx/proxy.conf
COPY --from=config /tmp/vhost.conf /etc/nginx/conf.d/default.conf