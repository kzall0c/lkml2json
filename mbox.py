#!/usr/bin/env python3.12
import argparse
import mailbox
import os
import re
import textwrap
import chardet # chardet 라이브러리 임포트

def extract_emails_with_headers(mbox_path, output_path, chunk_size=150):
    mbox = mailbox.mbox(mbox_path)
    total = len(mbox)
    file_idx = 0
    msg_in_chunk = 0
    out = None

    def open_new_file(idx):
        base, ext = os.path.splitext(output_path)
        filename = f"{base}-{idx:04d}{ext}"
        return open(filename, 'w', encoding='utf-8')

    for i, message in enumerate(mbox, 1):
        if msg_in_chunk == 0:
            if out:
                out.close()
            out = open_new_file(file_idx)
            file_idx += 1

        out.write(f'# {i}\n')
        out.write(f'Subject: {message.get("Subject", "")}\n')
        out.write(f'From: {message.get("From", "")}\n')
        out.write(f'To: {message.get("To", "")}\n')
        out.write(f'Date: {message.get("Date", "")}\n')

        body = ""

        if message.is_multipart():
            for part in message.walk():
                if part.get_content_type() == 'text/plain':
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset()

                    if charset and charset.lower() == 'unknown-8bit':
                        # chardet을 사용하여 인코딩 추정
                        detected_charset = chardet.detect(payload)['encoding']
                        if detected_charset:
                            try:
                                body += payload.decode(detected_charset, errors='replace')
                            except (UnicodeDecodeError, LookupError):
                                # 감지된 인코딩으로도 실패하면 'latin-1' 또는 'utf-8' fallback
                                body += payload.decode('latin-1', errors='replace')
                        else:
                            # chardet이 인코딩을 찾지 못하면 'latin-1' 또는 'utf-8' fallback
                            body += payload.decode('latin-1', errors='replace')
                    else:
                        # 기존 로직 (charset이 유효하거나 'utf-8' 기본값)
                        charset = charset or 'utf-8'
                        try:
                            body += payload.decode(charset, errors='strict')
                        except (UnicodeDecodeError, LookupError):
                            # 에러 발생 시 'replace' 옵션으로 'utf-8' 시도
                            body += payload.decode('utf-8', errors='replace')
        else:
            payload = message.get_payload(decode=True)
            charset = message.get_content_charset()

            if charset and charset.lower() == 'unknown-8bit':
                detected_charset = chardet.detect(payload)['encoding']
                if detected_charset:
                    try:
                        body += payload.decode(detected_charset, errors='replace')
                    except (UnicodeDecodeError, LookupError):
                        body += payload.decode('latin-1', errors='replace')
                else:
                    body += payload.decode('latin-1', errors='replace')
            else:
                charset = charset or 'utf-8'
                try:
                    body += payload.decode(charset, errors='strict')
                except (UnicodeDecodeError, LookupError):
                    body += payload.decode('utf-8', errors='replace')

        body = body.replace('\t', '    ') # 탭을 공백으로 변경

        out.write(body)
        out.write('\n\n')

        msg_in_chunk += 1
        if msg_in_chunk >= chunk_size:
            msg_in_chunk = 0

    if out:
        out.close()
    mbox.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="mbox에서 메일 헤더와 본문을 추출해 1만개씩 텍스트로 나눠 저장")
    parser.add_argument("mbox_path", help="입력 mbox 파일 경로")
    parser.add_argument("output_path", help="출력 텍스트 파일 경로(확장자 포함)")
    args = parser.parse_args()
    extract_emails_with_headers(args.mbox_path, args.output_path)
