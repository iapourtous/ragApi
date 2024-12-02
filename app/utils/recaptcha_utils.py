import logging
from flask import current_app
import requests


def verify_recaptcha(token,action):
    """
    Valide un token reCAPTCHA avec l'API reCAPTCHA Enterprise.
    
    Args:
        token (str): Le token reCAPTCHA fourni par le client
        action (str): L'action attendue (ex: 'LOGIN', 'REGISTER')
        
    Returns:
        tuple: (success: bool, score: float)
            - success: True si la validation est réussie
            - score: Score de risque entre 0 et 1
    """
    # Replace with your project ID
    PROJECT_ID = 'formal-outpost-271911'

    # Get the API key and site key from your Flask app configuration
    API_KEY = current_app.config['RECAPTCHA_API_KEY']      # Add this to your config
    SITE_KEY = current_app.config['RECAPTCHA_SITE_KEY']    # Add this to your config

    # Build the URL
    url = f'https://recaptchaenterprise.googleapis.com/v1/projects/{PROJECT_ID}/assessments?key={API_KEY}'

    # Create the request payload
    payload = {
        "event": {
            "token": token,
            "siteKey": SITE_KEY,
            "expectedAction": action,
        }
    }

    # Set the headers
    headers = {
        'Content-Type': 'application/json',
    }

    # Send the POST request to reCAPTCHA Enterprise API
    response = requests.post(url, json=payload, headers=headers)
    result = response.json()

    # Log the response for debugging
    logging.info(f"reCAPTCHA Enterprise response: {result}")

    # Check if the token is valid
    if 'tokenProperties' in result:
        token_properties = result['tokenProperties']
        if token_properties.get('valid'):
            # Token is valid
            # Get the risk analysis score
            risk_analysis = result.get('riskAnalysis', {})
            score = risk_analysis.get('score', 0.0)
            return True, score
        else:
            # Token is invalid, log the reason
            invalid_reason = token_properties.get('invalidReason')
            logging.warning(f"Invalid reCAPTCHA token: {invalid_reason}")
            return False, 0.0
    else:
        # Error in the response
        error = result.get('error', {})
        logging.error(f"Error in reCAPTCHA validation: {error}")
        return False, 0.0