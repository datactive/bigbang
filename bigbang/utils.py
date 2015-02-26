def remove_quoted(mess):
    mess.split('\n')
    message = list()
    for l in mess.split('\n'):
        n = len(l)
        if(len(l)!=0 and l[0] != '>' and l[n-6:n] != 'wrote:'):
            message.append(l)
    new = str()
    for l in message:
        new = new + l + '\n'
    return new

## remove this when clean_message is added to generic libraries
def clean_message(mess):
    if mess is None:
        mess = ''
    
    mess = remove_quoted(mess)

    return mess

