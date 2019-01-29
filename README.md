# filedrop
Anonymous file upload to S3 using Python/Flask

# Based on
* S3 anonymous uploading with python:
  * https://devcenter.heroku.com/articles/s3-upload-python
  * Anonymous-write S3 buckets need a special user, a special policy and a special CORS config
    * http://stackoverflow.com/questions/11916179/s3-anonymous-upload-key-prefix
    * http://docs.aws.amazon.com/AmazonS3/latest/dev/cors.html#how-do-i-enable-cors
* reCAPTCHA v2 to reduce uploads by robots
  * https://developers.google.com/recaptcha/docs/display
  * You must obtain an API key pair for your site to use this software:
    * http://www.google.com/recaptcha/admin
* Flask, Nginx and Ubuntu 16
  * https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-uwsgi-and-nginx-on-ubuntu-16-04

# Quick-start guide for nginx/Ubuntu 16,18
  * create a user called `filedrop` in the `www-data` group (group used by `nginx`)
```
        sudo adduser  --disabled-password --gecos "" --ingroup www-data filedrop
```
  * login as `filedrop`, get and install the repo
```
    git clone https://github.com/igg/FileDrop.git
    cd FileDrop
    virtualenv venv --no-site-packages
    source venv/bin/activate
    pip install -e .
```
  * SSL configuration is beyond the scope of these docs. Try:
    * https://www.digitalocean.com/community/tutorials/how-to-secure-nginx-with-let-s-encrypt-on-ubuntu-16-04
    * As specified in `startup/nginx/filedrop`, you  will need to make sure your ssl cert and key are at (or symlinked from):
    ```
          /etc/ssl/private/server-cert.pem
          /etc/ssl/private/server-cert-key.pem
    ```
    * You will need to manually change the name of your server from `filedrop.example.com` in `startup/nginx/filedrop`
  * copy startup files to appropriate places
    * switch back to your regular user with `sudo` privileges
      * `filedrop` user should not have a password or sudo privileges.
```
    sudo cp ~filedrop/FileDrop/startup/nginx/filedrop /etc/nginx/sites-available/
    sudo ln -s /etc/nginx/sites-available/filedrop /etc/nginx/sites-enabled/filedrop
    sudo cp ~filedrop/FileDrop/startup/systemd/filedrop.service /etc/systemd/system/filedrop.service
    sudo systemctl daemon-reload
    sudo service filedrop start
    sudo service nginx reload
```
