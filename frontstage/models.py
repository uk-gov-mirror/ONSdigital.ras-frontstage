import enum
import logging

import phonenumbers
from flask_wtf import FlaskForm
from phonenumbers.phonenumberutil import NumberParseException
from structlog import wrap_logger
from wtforms import HiddenField, PasswordField, StringField, SubmitField, TextAreaField, RadioField
from wtforms.validators import EqualTo, Length, Email, ValidationError, Required, Regexp
from frontstage.common.validators import InputRequired, DataRequired

from frontstage import app
from frontstage.i18n.translations import Translate

translations = Translate('form_messages')
_ = translations.translate

logger = wrap_logger(logging.getLogger(__name__))


class EnrolmentCodeForm(FlaskForm):
    enrolment_code = StringField(_('Enrolment Code'), [InputRequired(), Length(min=12,
                                                                               max=12,
                                                                               message=_('Re-enter the code and '
                                                                                         'try again'))])


class RegistrationForm(FlaskForm):
    first_name = StringField(_('First name'), validators=[InputRequired(_('First name is required')),
                                                          Length(max=254,
                                                                 message=_('Your first name must be less than 254 '
                                                                           'characters'))])
    last_name = StringField(_('Last name'),
                            validators=[InputRequired(_('Last name is required')),
                                        Length(max=254, message=_('Your last name must be less than 254 characters'))])
    email_address = StringField(_('Enter your email address'),
                                validators=[InputRequired(_('Email address is required')),
                                            Email(message=_('Invalid email address')),
                                            Length(max=254,
                                                   message=_('Your email must be less than 254 characters')),
                                            EqualTo('email_address_confirm',
                                                    message=app.config['EMAIL_MATCH_ERROR_TEXT'])])

    email_address_confirm = StringField(_('Re-type your email address'))

    password = PasswordField(_('Create a password'),
                             validators=[DataRequired(_('Password is required')),
                                         EqualTo('password_confirm', message=app.config['PASSWORD_MATCH_ERROR_TEXT']),
                                         Length(min=app.config['PASSWORD_MIN_LENGTH'],
                                                max=app.config['PASSWORD_MAX_LENGTH'],
                                                message=app.config['PASSWORD_CRITERIA_ERROR_TEXT'])])
    password_confirm = PasswordField(_('Re-type your password'))
    phone_number = StringField(_('Telephone number'),
                               validators=[DataRequired(_('Phone number is required')),
                                           Length(min=9,
                                                  max=15,
                                                  message=_('This should be a valid phone number between 9 and 15 '
                                                            'digits'))],
                               default=None)
    enrolment_code = HiddenField('Enrolment Code')

    @staticmethod
    def validate_phone_number(form, field):
        try:
            logger.info('Checking this is a valid phone number')
            input_number = phonenumbers.parse(field.data,
                                              'GB')  # Default region GB (44), unless country code added by user

            if not phonenumbers.is_possible_number(input_number):
                raise ValidationError(_('This should be a valid telephone number between 9 and 15 digits'))

            if not phonenumbers.is_valid_number(input_number):
                raise ValidationError(_('Please use a valid telephone number e.g. 01632 496 0018.'))
        except NumberParseException:
            logger.info('There is a number parse exception in the phonenumber field')
            raise ValidationError(_('This should be a valid telephone number e.g. 01632 496 0018. '))

    @staticmethod
    def validate_email_address(_, field):
        email = field.data
        return _validate_email_address(email)

    @staticmethod
    def validate_password(_, field):
        password = field.data
        if password.isalnum() or not any(char.isupper() for char in password) or not any(
                char.isdigit() for char in password):
            raise ValidationError(app.config['PASSWORD_CRITERIA_ERROR_TEXT'])


class LoginForm(FlaskForm):
    username = StringField(_('Email Address'), [InputRequired(_('Email Address is required')),
                                                Email(_('Invalid email address'))])
    password = PasswordField(_('Password'), [InputRequired(_('Password is required'))])

    @staticmethod
    def validate_username(form, field):
        email = field.data
        return _validate_email_address(email)


def _validate_email_address(email):
    """
    Validates an email address, using regex to conform to GDS standards.

    :param field:
        Field containing email address for validation.
    """
    local_part, domain_part = email.rsplit('@', 1)
    logger.info('Checking if the email address contains a space or quotes in the local part')
    # this extends the email validator to check if there is whitespace in the email or quotes surrounding local part
    if ' ' in email:
        logger.info('Space found in email address')
        raise ValidationError(_('Invalid email address'))
    if local_part.startswith('"') and local_part.endswith('"'):
        logger.info('Quotes found in local part of email')
        raise ValidationError(_('Invalid email address'))


class ForgotPasswordForm(FlaskForm):
    email_address = StringField(_('Enter your email address'),
                                validators=[InputRequired(_('Email address is required')),
                                            Email(message=_('Invalid email address')),
                                            Length(max=254,
                                                   message=_('Your email must be less than 254 characters'))])

    @staticmethod
    def validate_email_address(_, field):
        email = field.data
        return _validate_email_address(email)


class ResetPasswordForm(FlaskForm):
    password = PasswordField(_('New password'),
                             validators=[DataRequired(_('Password is required')),
                                         EqualTo('password_confirm', message=app.config['PASSWORD_MATCH_ERROR_TEXT']),
                                         Length(min=app.config['PASSWORD_MIN_LENGTH'],
                                                max=app.config['PASSWORD_MAX_LENGTH'],
                                                message=app.config['PASSWORD_CRITERIA_ERROR_TEXT'])])
    password_confirm = PasswordField(_('Re-type new password'))

    @staticmethod
    def validate_password(form, field):
        password = field.data
        if password.isalnum() or not any(char.isupper() for char in password) or not any(char.isdigit() for char in
                                                                                         password):
            raise ValidationError(app.config['PASSWORD_CRITERIA_ERROR_TEXT'])


class SecureMessagingForm(FlaskForm):
    send = SubmitField(label=_('Send'), id='send-message-btn')
    subject = StringField(_('Subject'))
    body = TextAreaField(_('Message'), validators=[DataRequired(_('Message is required')),
                                                   Length(max=50000,
                                                          message=_('Message must be less than 50000 '
                                                                    'characters'))])
    msg_id = HiddenField('Message id')
    thread_id = HiddenField('Thread id')
    hidden_subject = HiddenField('Hidden Subject')


class RespondentStatus(enum.IntEnum):
    CREATED = 0
    ACTIVE = 1
    SUSPENDED = 2


class OptionsForm(FlaskForm):
    option = RadioField('Label', choices=[
        ('value', 'contact_details'),
        ('value', 'change_password'),
        ('value', 'share_surveys')])

    def validate(self):
        if self.data['option'] is None:
            return False
        return True


class HelpOptionsForm(FlaskForm):
    option = RadioField('Label', choices=[
        ('value', 'help-completing-this-survey'),
        ('value', 'info-about-this-survey')
    ])

    def validate(self):
        if self.data['option'] is None:
            return False
        return True


class AccountSurveyShareBusinessSelectForm(FlaskForm):
    option = RadioField('Label')

    def validate(self):
        if self.data['option'] is None:
            return False
        return True


class AccountSurveyShareSurveySelectForm(FlaskForm):
    option = RadioField('Label')

    def validate(self):
        if self.data['option'] is None:
            return False
        return True


class HelpInfoAboutThisSurveyForm(FlaskForm):
    option = RadioField('Label', choices=[
        ('value', 'exemption-completing-survey'),
        ('value', 'why-selected'),
        ('value', 'time-to-complete'),
        ('value', 'how-long-selected-for'),
        ('value', 'penalties'),
        ('value', 'info-something-else')
    ])

    def validate(self):
        if self.data['option'] is None:
            return False
        return True


class HelpCompletingThisSurveyForm(FlaskForm):
    option = RadioField('Label', choices=[
        ('value', 'answer-survey-question'),
        ('value', 'do-not-have-specific-figures'),
        ('value', 'unable-to-return-by-deadline'),
        ('value', 'something-else'),
    ])

    def validate(self):
        if self.data['option'] is None:
            return False
        return True


class ContactDetailsChangeForm(FlaskForm):
    first_name = StringField(_('First name'), validators=[DataRequired(_('First name is required')),
                                                          Length(max=254,
                                                                 message=_('Your first name must be less than 254 '
                                                                           'characters'))])
    last_name = StringField(_('Last name'),
                            validators=[DataRequired(_('Last name is required')),
                                        Length(max=254, message=_('Your last name must be less than 254 characters'))])
    phone_number = StringField(_('Telephone number'),
                               validators=[DataRequired(_('Phone number is required')),
                                           Length(min=9,
                                                  max=15,
                                                  message=_('This should be a valid phone number between 9 and 15 '
                                                            'digits'))],
                               default=None)
    # TODO: Remove comments and delete the field without validation once email change functionality is enabled.
    # This was commented out rather then feature flagged as it's difficult to feature flag a model.
    email_address = StringField(_('Email address'))
    # email_address = StringField(_('Email address'),
    #                             validators=[DataRequired(_('Email address is required')),
    #                                         Email(message=_('Invalid email address')),
    #                                         Length(max=254,
    #                                                message=_('Your email must have fewer than 254 characters'))])


class ConfirmEmailChangeForm(FlaskForm):
    email_address = HiddenField('Email address')


class ChangePasswordFrom(FlaskForm):
    password = PasswordField(_('type your password'),
                             validators=[DataRequired(_('Your current password is required'))])

    new_password = PasswordField(_('Create a new password'),
                                 validators=[DataRequired(_('Your new password is required')),
                                             EqualTo('new_password_confirm',
                                                     message=app.config['PASSWORD_MATCH_ERROR_TEXT']),
                                             Length(min=app.config['PASSWORD_MIN_LENGTH'],
                                                    max=app.config['PASSWORD_MAX_LENGTH'],
                                                    message=app.config['PASSWORD_CRITERIA_ERROR_TEXT'])])
    new_password_confirm = PasswordField(_('Re-type your new password'))

    @staticmethod
    def validate_new_password(form, field):
        new_password = field.data
        if new_password.isalnum() or not any(char.isupper() for char in new_password) or not any(
                char.isdigit() for char in
                new_password):
            raise ValidationError(app.config['PASSWORD_CRITERIA_ERROR_TEXT'])


class AccountSurveyShareRecipientEmailForm(FlaskForm):
    email_address = StringField(_('Enter recipient email address'),
                                validators=[InputRequired(_("You need to enter an email address")),
                                            Email(message=_('Invalid email address')),
                                            Length(max=254,
                                                   message=_('Your email must be less than 254 characters'))])

    @staticmethod
    def validate_email_address(_, field):
        email = field.data
        return _validate_email_address(email)
