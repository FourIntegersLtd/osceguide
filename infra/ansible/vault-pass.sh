#!/usr/bin/env bash
# Ansible calls this for the vault password (ansible.cfg vault_password_file).
exec security find-generic-password -a "$USER" -s osceguide-ansible-vault -w
