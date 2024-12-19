#!/usr/bin/env bash

export PYTHONPATH="${PYTHONPATH}:${PWD}/custom_components"

hass --config "${PWD}/config" --debug
