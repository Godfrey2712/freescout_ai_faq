# FREESCOUT AI FAQ GENERATOR


## Getting started

This project is setup to generate AI FAQs from FreeScout API. It also displays the original conversational thread, the AI generated FAQ, and the ability to edit the AI generated FAQs.

## Test and Deploy

1. Get a cloud server setup (new droplets, etc)
2. Pull the project locally
3. Add a .env file to the project root dir with these variables `api_key` set to the value of the OpenAI API key, and `freeScout_api_key` set to the value of the FreeScout API Key. For example in the .env file: `api_key = xyz with no ''`
4. Upload the project to the server instance setup
5. While project is on the server, on the root directory, run:
    `docker-compose up --build`
6. Once the container is running, try accessing it's content using the server IP Address at the container's port

## Deploy with CI-CD

## For Devs

### Standards to follow!

## Usage
### Fields available in the UI:
1. Mail-id:
2. Page-size:
3. Model:
4. Temperature: 

## License
Project is currently unlicensed, and all rights are associated with CONVOSTEM LTD.

## Project status
Currently under AB testing.

## Changelog
