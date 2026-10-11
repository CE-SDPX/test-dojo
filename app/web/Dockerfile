FROM nginx:1.27-alpine

COPY . /usr/share/nginx/html
RUN rm -f /usr/share/nginx/html/Dockerfile /usr/share/nginx/html/docker-entrypoint.sh \
    /usr/share/nginx/html/nginx.conf.template

COPY nginx.conf.template /etc/nginx/conf.d/default.conf
COPY docker-entrypoint.sh /docker-entrypoint.d/50-dojo-config.sh
RUN chmod +x /docker-entrypoint.d/50-dojo-config.sh

EXPOSE 80
