#!/usr/bin/env python3.12
import argparse
import mailbox
import os
import json
import csv
import chardet

def extract_emails(mbox_path, output_path, fmt='json', chunk_size=150):
    mbox = mailbox.mbox(mbox_path)
    file_idx = 0
    msg_in_chunk = 0
    emails = []

    def open_new_file(idx, mode='w', newline=''):
        base, ext = os.path.splitext(output_path)
        filename = f"{base}-{idx:04d}{ext}"
        return open(filename, mode, encoding='utf-8', newline=newline)

    def decode_payload(payload, charset):
        if charset and charset.lower() == 'unknown-8bit':
            detected_charset = chardet.detect(payload)['encoding']
            charset = detected_charset or 'latin-1'
        else:
            charset = charset or 'utf-8'

        try:
            return payload.decode(charset, errors='replace')
        except (UnicodeDecodeError, LookupError):
            return payload.decode('utf-8', errors='replace')

    if fmt == 'csv':
        out = open_new_file(file_idx, mode='w', newline='')
        writer = csv.DictWriter(out, fieldnames=["index", "subject", "from", "to", "date", "body"])
        writer.writeheader()
    else:
        out = open_new_file(file_idx)

    for i, message in enumerate(mbox, 1):
        email_obj = {
            "index": i,
            "subject": message.get("Subject", ""),
            "from": message.get("From", ""),
            "to": message.get("To", ""),
            "date": message.get("Date", "")
        }

        body = ""

        if message.is_multipart():
            for part in message.walk():
                if part.get_content_type() == 'text/plain':
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset()
                        body += decode_payload(payload, charset)
        else:
            payload = message.get_payload(decode=True)
            if payload:
                charset = message.get_content_charset()
                body += decode_payload(payload, charset)

        email_obj["body"] = body.replace('\t', '    ')

        if fmt == 'jsonl':
            out.write(json.dumps(email_obj, ensure_ascii=False) + "\n")
        elif fmt == 'csv':
            writer.writerow(email_obj)
        else:  # json
            emails.append(email_obj)

        msg_in_chunk += 1
        if msg_in_chunk >= chunk_size:
            if fmt == 'json' and emails:
                out.write(json.dumps(emails, ensure_ascii=False, indent=2))
                emails = []
            out.close()
            msg_in_chunk = 0
            file_idx += 1
            if fmt == 'csv':
                out = open_new_file(file_idx, mode='w', newline='')
                writer = csv.DictWriter(out, fieldnames=["index", "subject", "from", "to", "date", "body"])
                writer.writeheader()
            else:
                out = open_new_file(file_idx)

    if fmt == 'json' and emails:
        out.write(json.dumps(emails, ensure_ascii=False, indent=2))

    out.close()
    mbox.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="mbox에서 메일을 추출해 JSON, JSONL 또는 CSV 형식으로 저장")
    parser.add_argument("mbox_path", help="입력 mbox 파일 경로")
    parser.add_argument("output_path", help="출력 파일 경로 (확장자 포함)")
    parser.add_argument("--format", choices=["json", "jsonl", "csv"], default="json", help="출력 형식 선택 (기본: json)")
    args = parser.parse_args()
    extract_emails(args.mbox_path, args.output_path, fmt=args.format)

