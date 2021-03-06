from pyslideshare import pyslideshare
from localsettings import username, password, api_key, secret_key
requires_for_uploading =['username', 'password',
                         'slideshow_title', 'slideshow_srcfile', 'slideshow_description',
                         'slideshow_tags', 'make_src_public', 'make_slideshow_private',
                         'generate_secret_url', 'allow_embeds', 'share_with_contacts']
def get_by_tag(obj):
    tag = input('which presentation tag are you looking for?\n')
    number = input('How much presentation you want to see? Enter for pass\n')
    try:
        int(number)
    except ValueError:
        print('Incorrect number')
    if type(number) == int:
        obj.get_slideshow_by_tag(limit=number, tag=tag)
    else:
        obj.get_slideshow_by_tag(tag=tag)


def count_by_tag(obj):
    pass


def get_by_user(obj):
    number = input('How much presentation you want to see?\n')
    obj.get_slideshow_by_user(limit=number)


def count_by_user(obj):
    pass


def download_slideshow(obj):
    id = input('Which slideshow you want to download?(id required)\n')
    obj.download_slideshow(slideshow_id = id)


def upload_slideshow(obj):
    upload_params = {}
    print('in make_src_public, make_slideshow_private,'+
          ' generate_secret_urr, allow_embeds, share_with_contacts "Y" or "N" required')
    for i in range(len(requires_for_uploading)):
        upload_params[requires_for_uploading[i]] = input(str(requires_for_uploading[i]))
    obj.upload_slideshow(username=upload_params['username'], password=upload_params['password'],
                         slideshow_title=upload_params['slideshow_title'],
                         slideshow_srcfile=upload_params['slideshow_srcfile'],
                         slideshow_description=upload_params['slideshow_descriptions'],
                         slideshow_tags=upload_params['slideshow_tags'],
                         make_src_public=upload_params['make_src_public'],
                         make_slideshow_private=upload_params['make_slideshow_private'],
                         generate_secret_url=upload_params['generate_secret_url'],
                         allow_embeds=upload_params['allow_embeds'],
                         share_with_contacts=upload_params['share_with_contacts']
                         )


def delete_slideshow(obj):
    id = input('Write slideshow id you want to delete: ')
    obj.detele_slideshow(slideshow_id=id)
