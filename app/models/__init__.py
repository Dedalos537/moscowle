# ruff: noqa: I001  (el orden de estos imports es deliberado: evita ciclos entre modelos)
from app.models.admin import *
from app.models.ai import *
from app.models.ai_provider import AIProvider as AIProvider
from app.models.ai_provider import AISettings as AISettings
from app.models.appointment import *
from app.models.bot_config import BotConfig as BotConfig
from app.models.bot_conversation import BotConversation as BotConversation
from app.models.bot_conversation import BotMessage as BotMessage
from app.models.print_job import PrintJob as PrintJob
from app.models.server_snapshot import ServerSnapshot as ServerSnapshot
from app.models.system_setting import LiveVersion as LiveVersion
from app.models.system_setting import SystemSetting as SystemSetting
from app.models.chat import *
from app.models.contract import *
from app.models.faq import Faq as Faq
from app.models.faq_unanswered import FaqUnanswered as FaqUnanswered
from app.models.game import *
from app.models.holiday import Holiday as Holiday
from app.models.incidente import *
from app.models.kanban import *
from app.models.notification import *
from app.models.password_reset import PasswordReset as PasswordReset
from app.models.patient_group import *
from app.models.payment import *
from app.models.refresh_token import RefreshToken as RefreshToken
from app.models.report import *
from app.models.service_request import *
from app.models.chat_login_code import ChatLoginCode as ChatLoginCode
from app.models.email_throttle import EmailThrottle as EmailThrottle
from app.models.telegram_user import TelegramUser as TelegramUser
from app.models.user import *
from app.models.user_session import UserSession as UserSession
from app.models.user_status_log import UserStatusLog as UserStatusLog
from app.models.webauthn import WebAuthnChallenge as WebAuthnChallenge
from app.models.webauthn import WebAuthnCredential as WebAuthnCredential
from app.models.message_log import MessageLog as MessageLog
from app.models.message_template import MessageTemplate as MessageTemplate
from app.models.campaign import Campaign as Campaign
from app.models.campaign import CampaignSend as CampaignSend
from app.models.action_request import ActionRequest as ActionRequest
