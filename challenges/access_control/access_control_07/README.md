# Access Control 07 — nginx Config Injection

## Objective
The directory `/etc/nginx/conf.d/` has world-writable permissions, and a root cron job validates and reloads the nginx configuration every minute. nginx runs as root. The goal is to inject a malicious nginx configuration file that causes nginx to execute a command or expose the flag when the cron job reloads.

## Connect
```
ssh student@localhost -p 2207
```
Password: `password`

## Vulnerability
`/etc/nginx/conf.d/` is set to `chmod 777`, allowing the student user to create or overwrite configuration files. The cron entry `* * * * * root nginx -t && nginx -s reload` runs as root and picks up any new configs. nginx directives such as `access_log` with a pipe or abuse of Lua modules can be exploited to run commands as root.

## Hint
nginx config directives that write to paths can be abused — look at what happens when you configure nginx to serve or log to unexpected locations.

## Flag location
`/root/flag.txt`
