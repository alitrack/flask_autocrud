from decimal import Decimal
from datetime import datetime

from .model import Model

from .config import HTTP_STATUS
from .config import COLLECTION_SUFFIX


def from_model_to_dict(data):
    """

    :param data:
    :return:
    """
    resp = {}

    if not isinstance(data, dict):
        data = data.__dict__

    for k, v in data.items():
        if k.startswith('_'):
            continue

        if isinstance(v, Model):
            resp.update({
                v.__class__.__name__: from_model_to_dict(v)
            })
        elif isinstance(v, list):
            if len(v) > 0:
                name = v[0].__class__.__name__ + COLLECTION_SUFFIX
                resp.update({
                    name: [from_model_to_dict(i) for i in v]
                })
        else:
            if isinstance(v, Decimal):
                v = float(v)
            elif isinstance(v, datetime):
                v = v.isoformat()

            resp.update({k: v})
    return resp


def validate_entity(model, data):
    """

    :param model:
    :param data:
    """
    fields = model.required() + model.optional()
    unknown = [k for k in data if k not in fields]
    missing = list(set(model.required()) - set(data.keys()))

    return missing if len(missing) else None, unknown if len(unknown) else None


def links_header(resource):
    """

    :param resource:
    :return:
    """
    links = resource.links()
    link_string = '<{}>; rel=self'.format(links['self'])

    for k, l in links.items():
        if k != 'self':
            link_string += ', <{}>; rel=related'.format(l)

    return {'Link': link_string}


def location_header(resource):
    """

    :param resource:
    :return:
    """
    location = resource.links()
    return {'Location': location['self']}


def pagination_headers(pagination):
    """

    :param pagination:
    :return:
    """
    code = HTTP_STATUS.SUCCESS

    total_results = pagination.total_results
    page_number = pagination.page_number
    num_pages = pagination.num_pages
    page_size = pagination.page_size

    if num_pages > 1 and total_results > page_size:
        code = HTTP_STATUS.PARTIAL_CONTENT

    if page_number == num_pages:
        code = HTTP_STATUS.SUCCESS

    return {
        'Pagination-Count': total_results,
        'Pagination-Page': page_number,
        'Pagination-Num-Pages': num_pages,
        'Pagination-Limit': page_size
    }, code
