import urllib2
import urllib
import gzip
import re
import os
import urlparse
import logging
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
import email
import email.parser
import mailbox
import time
import bigbang.mailman
import dateutil
from . import parse

class W3cMailingListArchivesParser(email.parser.Parser):
    parse = None
    # doesn't yet implement the file version

    # takes the full HTML of a single message page; returns an email Message
    # currently returns an mboxMessage, with appropriate From separator line
    # TODO: parse To, CC (Archived-At?, others?) headers
    # TODO: support headersonly option
    # TODO: ignore spam (has separate error message in w3c archives)
    def parsestr(self, text, headersonly=None):
        soup = BeautifulSoup(text)
        body = self._text_for_selector(soup, '#body')
        msg = MIMEText(body, 'plain', 'utf-8')

        from_text = self._parse_dfn_header(
            self._text_for_selector(
                soup,
                '#from'))
        from_name = from_text.split('<')[0].strip()
        from_address = self._text_for_selector(soup, '#from a')

        from_addr = email.utils.formataddr((from_name, from_address))
        msg['From'] = from_addr

        subject = self._text_for_selector(soup, 'h1')
        msg['Subject'] = subject

        message_id = self._parse_dfn_header(
            self._text_for_selector(
                soup,
                '#message-id'))
        msg['Message-ID'] = message_id.strip()

        message_date = self._parse_dfn_header(
            self._text_for_selector(
                soup,
                '#date'))
        msg['Date'] = message_date.strip()

        mbox_message = mailbox.mboxMessage(msg)
        mbox_message.set_from(
            from_address,
            email.utils.parsedate(message_date))

        return mbox_message

    def _parse_dfn_header(self, header_text):
        header_texts = header_text.split(':', 1)
        if len(header_texts) == 2:
            return header_texts[1]
        else:
            logging.warning("Split failed on %s", header_text)
            return ''

    def _text_for_selector(self, soup, selector):
        results = soup.select(selector)
        if results:
            result = results[0].get_text()
        else:
            result = ''
            logging.warning('No matching text for selector %s', selector)

        return unicode(result).encode('utf-8')

def normalize_mailing_list_url(url):
    if not url.endswith('/'):
        return url + '/'
    
    return url

def collect_from_url(url, base_arch_dir="archives", notes=None):
    """
    Collects W3C mailing list archives from a particular mailing list URL.

    Logs an error and returns False if no messages can be collected.
    """
    url = normalize_mailing_list_url(url)
    list_name = bigbang.mailman.get_list_name(url)
    logging.info("Getting W3C list archive for %s", list_name)

    try:
        response = urllib2.urlopen(url)
        html = response.read()
        soup = BeautifulSoup(html)
    except urllib2.HTTPError as exception:
        logging.exception('Error in loading W3C list archive page for %s', url)
        return False

    try:
        time_period_indices = list()
        rows = soup.select('tbody tr')
        for row in rows:
            link = row.select('td:nth-of-type(1) a')[0].get('href')
            logging.info("Found time period archive page: %s", link)
            time_period_indices.append(link)
    except Exception as exception:
        logging.exception('Error in parsing list archives for %s', url)
        return False

    # directory for downloaded files
    arc_dir = bigbang.mailman.archive_directory(base_arch_dir, list_name)
    bigbang.mailman.populate_provenance(directory=arc_dir, list_name=list_name, list_url=url, notes=notes)

    for link in time_period_indices:
        link_url = urlparse.urljoin(url, link)
        response = urllib2.urlopen(link_url)
        html = response.read()
        soup = BeautifulSoup(html)

        end_date_string = soup.select(
            '#end')[0].parent.parent.select('em')[0].get_text()
        end_date = dateutil.parser.parse(end_date_string)
        year_month_mbox = end_date.strftime('%Y-%m') + '.mbox'
        mbox_path = os.path.join(arc_dir, year_month_mbox)

        # looks like we've already downloaded this timeperiod
        if os.path.isfile(mbox_path):
            logging.info(
                'Looks like %s already exists, moving on.', mbox_path)
            continue
        logging.info('Downloading messages to archive to %s.', mbox_path)

        message_links = list()
        messages = list()

        anchors = soup.select('div.messages-list a')
        for anchor in anchors:
            if anchor.get('href'):
                message_url = urlparse.urljoin(link_url, anchor.get('href'))
                message_links.append(message_url)

        for message_link in message_links:
            response = urllib2.urlopen(message_link)
            html = response.read()

            message = W3cMailingListArchivesParser().parsestr(html)
            messages.append(message)
            time.sleep(1)  # wait between loading messages, for politeness

        mbox = mailbox.mbox(mbox_path)
        mbox.lock()

        try:
            for message in messages:
                mbox.add(message)
            mbox.flush()
        finally:
            mbox.unlock()

        logging.info('Saved %s', year_month_mbox)

    # assumes all archives were downloaded if no exceptions have been thrown
    provenance = bigbang.mailman.access_provenance(arc_dir)
    provenance['complete'] = True
    bigbang.mailman.update_provenance(arc_dir, provenance)

