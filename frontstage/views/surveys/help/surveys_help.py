import json
import logging

from markupsafe import Markup
from structlog import wrap_logger
from flask import render_template, request, make_response, url_for, flash
from werkzeug.utils import redirect

from frontstage.common.authorisation import jwt_authorization
from frontstage.controllers import survey_controller, conversation_controller
from frontstage.models import HelpOptionsForm, HelpCompletingMonthlyBusinessSurveyForm, SecureMessagingForm
from frontstage.views.surveys import surveys_bp

logger = wrap_logger(logging.getLogger(__name__))


@surveys_bp.route('/help/<short_name>/<business_id>', methods=['GET'])
@jwt_authorization(request)
def get_help_page(session, short_name, business_id):
    survey = survey_controller.get_survey_by_short_name(short_name)
    return render_template('surveys/help/surveys-help.html',
                           form=HelpOptionsForm(),
                           short_name=short_name, survey_name=survey['longName'], business_id=business_id)


@surveys_bp.route('/help/<short_name>/<business_id>', methods=['POST'])
@jwt_authorization(request)
def post_help_page(session, short_name, business_id):
    form = HelpOptionsForm(request.values)
    form_valid = form.validate()
    if form.data['option'] == 'help-completing-this-survey':
        return redirect(url_for('surveys_bp.get_help_option_select', short_name=short_name, business_id=business_id,
                                option='help-completing-this-survey'))


@surveys_bp.route('/help/<short_name>/<business_id>/<option>', methods=['GET'])
@jwt_authorization(request)
def get_help_option_select(session, short_name, business_id, option):
    survey = survey_controller.get_survey_by_short_name(short_name)
    if option == 'help-completing-this-survey':
        return render_template('surveys/help/surveys-help-completing-this-survey.html',
                               short_name=short_name, business_id=business_id, option=option,
                               form=HelpCompletingMonthlyBusinessSurveyForm(),
                               survey_name=survey['longName'])


@surveys_bp.route('/help/<short_name>/<business_id>/<option>', methods=['POST'])
@jwt_authorization(request)
def post_help_option_select(session, short_name, business_id, option):
    if option == 'help-completing-this-survey':
        form = HelpCompletingMonthlyBusinessSurveyForm(request.values)
        form_valid = form.validate()
        breadcrumbs_title = 'Help completing this survey'
        if form.data['option'] == 'answer-survey-question':
            return redirect(url_for('surveys_bp.get_send_help_message', short_name=short_name,
                                    option=option, business_id=business_id))
        if form.data['option'] == 'do-not-have-specific-figures':
            return redirect(url_for('surveys_bp.get_help_option_sub_option_select', short_name=short_name,
                                    option=option, sub_option='do-not-have-specific-figures',
                                    business_id=business_id))
        if form.data['option'] == 'unable-to-return-by-deadline':
            return redirect(url_for('surveys_bp.get_help_option_sub_option_select', short_name=short_name,
                                    option=option, sub_option='unable-to-return-by-deadline',
                                    business_id=business_id))
        if form.data['option'] == 'something-else':
            return render_template('secure-messages/help/secure-message-send-messages-view.html',
                                   short_name=short_name, option=option, form=SecureMessagingForm(),
                                   subject='Help completing this survey', text_one=breadcrumbs_title,
                                   business_id=business_id
                                   )


@surveys_bp.route('/help/<short_name>/<business_id>/<option>/<sub_option>', methods=['GET'])
@jwt_authorization(request)
def get_help_option_sub_option_select(session, short_name, business_id, option, sub_option):
    if sub_option == 'do-not-have-specific-figures':
        return render_template('surveys/help/surveys-help-specific-figure-for-response.html',
                               short_name=short_name, option=option, sub_option=sub_option,
                               subject='Help answering a survey question',
                               breadcrumbs=[{"text": "Help completing this survey"}, {}],
                               business_id=business_id)
    if sub_option == 'unable-to-return-by-deadline':
        return render_template('surveys/help/surveys-help-return-data-by-deadline.html',
                               short_name=short_name, option=option, sub_option=sub_option,
                               subject='Help answering a survey question',
                               breadcrumbs=[{"text": "Help completing this survey"}, {}],
                               business_id=business_id)


@surveys_bp.route('/help/<short_name>/<business_id>/<option>/send-message', methods=['GET'])
@jwt_authorization(request)
def get_send_help_message(session, short_name, business_id, option):
    if option == 'help-completing-this-survey':
        breadcrumbs_title = 'Help completing this survey'
    return render_template('secure-messages/help/secure-message-send-messages-view.html',
                           short_name=short_name, option=option, form=SecureMessagingForm(),
                           subject='Help answering a survey question', text_one=breadcrumbs_title,
                           business_id=business_id
                           )


@surveys_bp.route('/help/<short_name>/<business_id>/<option>/<sub_option>/send-message', methods=['GET'])
@jwt_authorization(request)
def get_send_help_message_page(session, short_name, business_id, option, sub_option):
    subject, text_one, text_two = get_subject_and_breadcrumbs_title(sub_option, f'surveys/help/{short_name}/{option}')
    return render_template('secure-messages/help/secure-message-send-messages-view.html',
                           short_name=short_name, option=option, sub_option=sub_option, form=SecureMessagingForm(),
                           subject=subject, text_one=text_one, text_two=text_two, business_id=business_id)


@surveys_bp.route('/help/<short_name>/<business_id>/send-message', methods=['POST'])
@jwt_authorization(request)
def send_help_message(session, short_name, business_id):
    subject = request.args['subject']
    party_id = session.get_party_id()
    survey = survey_controller.get_survey_by_short_name(short_name)
    business_id = business_id
    form = SecureMessagingForm(request.form)
    if form.validate():
        logger.info("Form validation successful", party_id=party_id)
        sent_message = _send_new_message(subject, party_id, survey['id'], business_id)
        thread_url = url_for("secure_message_bp.view_conversation",
                             thread_id=sent_message['thread_id']) + "#latest-message"
        flash(Markup(f'Message sent. <a href={thread_url}>View Message</a>'))
        return redirect(url_for('surveys_bp.get_survey_list', tag='todo'))


def _send_new_message(subject, party_id, survey, business_id):
    logger.info('Attempting to send message', party_id=party_id, business_id=business_id)
    form = SecureMessagingForm(request.form)
    message_json = {
        "msg_from": party_id,
        "msg_to": ['GROUP'],
        "subject": subject,
        "body": form['body'].data,
        "thread_id": form['thread_id'].data,
        "business_id": business_id,
        "survey": survey,
    }

    response = conversation_controller.send_message(json.dumps(message_json))

    logger.info('Secure message sent successfully',
                message_id=response['msg_id'], party_id=party_id, business_id=business_id)
    return response


def get_subject_and_breadcrumbs_title(option, uri):
    if option == 'do-not-have-specific-figures':
        return 'I don’t have specific figures for a response', \
               "Help completing this survey", \
               "I don’t have specific figures for a response"
    if option == 'unable-to-return-by-deadline':
        return 'I’m unable to return the data by the deadline', \
               "Help completing this survey", \
               "I’m unable to return the data by the deadline"