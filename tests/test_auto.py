import pytest

from . import create_app
from . import assert_export


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    _client = app.test_client()
    return _client


def test_app_runs(client):
    res = client.get('/')
    assert res.status_code == 404


def test_resources_list_json(client):
    res = client.get('/resources')
    assert res.status_code == 200
    assert res.headers.get('Content-Type') == 'application/json'


def test_resources_list_xml(client):
    res = client.get(
        '/resources',
        headers={'Accept': 'application/xml'}
    )
    assert res.status_code == 200
    assert res.headers.get('Content-Type') == 'application/xml; charset=utf-8'


def test_bad_request(client):
    res = client.post('/artist')
    assert res.status_code == 400

    res = client.put('/artist/1')
    assert res.status_code == 400


def test_not_found(client):
    res = client.delete('/artist/1000000000')
    assert res.status_code == 404

    res = client.get('/artist/1000000000')
    assert res.status_code == 404


def test_conflict(client):
    res = client.post(
        '/artist',
        json={'Name': 'Accept'},
        headers={'Accept': 'application/xml'}
    )
    assert res.status_code == 409
    assert res.headers.get('Content-Type') == 'application/xml; charset=utf-8'


def test_update(client):
    res = client.get('/artist/1')
    etag = res.headers.get('ETag')

    res = client.put(
        '/artist/1',
        json={'Name': 'pippo2'},
        headers={'If-Match': etag}
    )
    etag = res.headers.get('ETag')
    assert res.status_code == 200
    assert etag is not None

    res = client.patch(
        '/artist/1',
        json={'Name': 'pippo3'},
        headers={'If-Match': etag}
    )
    assert res.status_code == 200


def test_unprocessable_entity(client):
    res = client.post(
        '/artist',
        json={'pippo': 'pluto'}
    )
    assert res.status_code == 422
    assert res.headers.get('Content-Type') == 'application/json'

    res = client.put(
        '/artist/1',
        json={'pippo': 'pluto'}
    )
    assert res.status_code == 422
    assert res.headers.get('Content-Type') == 'application/json'

    res = client.patch(
        '/artist/1',
        json={'pippo': 'pluto'}
    )
    assert res.status_code == 422
    assert res.headers.get('Content-Type') == 'application/json'


def test_resource_crud(client):
    res = client.post(
        '/artist',
        json={'Name': 'pippo'}
    )
    assert res.status_code == 201
    assert res.headers.get('Content-Type') == 'application/json'

    data = res.get_json()
    id = data.get('ArtistId')

    etag = res.headers.get('ETag')
    assert etag is not None
    assert res.headers.get('Location').endswith('/artist/{}'.format(id))

    res = client.get('/artist/{}'.format(id))
    etag = res.headers.get('ETag')

    assert res.status_code == 200
    assert etag is not None
    assert res.headers.get('Content-Type') == 'application/json'
    assert res.headers.get('Link') == "</artist/{id}>; rel=self, </artist/{id}/album>; rel=related".format(id=id)

    data = res.get_json()
    returned_id = data.get('ArtistId')
    assert returned_id == id

    res = client.get('/artist/{}'.format(id), headers={'If-None-Match': etag})
    assert res.status_code == 304

    res = client.get('/artist/{}'.format(id), headers={'If-None-Match': 'fake_etag'})
    assert res.status_code == 200

    etag = res.headers.get('ETag')
    res = client.delete('/artist/{}'.format(id))
    assert res.status_code == 428

    res = client.delete('/artist/{}'.format(id), headers={'If-Match': 'fake_etag'})
    assert res.status_code == 412

    res = client.delete('/artist/{}'.format(id), headers={'If-Match': etag})
    assert res.status_code == 204


def test_put_creation(client):
    id_res = 123456

    res = client.put(
        '/some_model/{}'.format(id_res),
        json={'value': 'pippo'}
    )
    assert res.status_code == 201
    etag = res.headers.get('ETag')
    assert etag is not None
    assert res.get_json().get('id') == id_res

    res = client.get('/some_model/{}'.format(id_res), headers={'If-Match': etag})
    assert res.status_code == 200
    etag = res.headers.get('ETag')
    assert etag is not None
    assert res.get_json().get('id') == id_res

    res = client.delete('/some_model/{}'.format(id_res), headers={'If-Match': etag})
    assert res.status_code == 204


def test_put_failed(client):
    res = client.put(
        '/some_model/10',
        json={'pippo': 'pluto'}
    )
    assert res.status_code == 422

    data = res.get_json()['response']
    missing = data.get('missing')
    unknown = data.get('unknown')
    assert len(missing) == 1
    assert len(unknown) == 1
    assert missing[0] == 'value'
    assert unknown[0] == 'pippo'


def test_resource_meta(client):
    res = client.get('/artist/meta')
    assert res.status_code == 200
    assert res.headers.get('Content-Type') == 'application/json'

    data = res.get_json()
    assert all(i in data.keys() for i in (
        'name',
        'description',
        'fields',
        'methods',
        'url'
    ))


def test_get_list(client):
    res = client.get('/artist')
    assert res.status_code == 200


def test_hateoas(client):
    res = client.get('/artist/1')
    assert res.status_code == 200

    data = res.get_json()
    assert '_links' in data.keys()
    assert data['_links'].get('self') == '/artist/1'


def test_export(client):
    res = client.get('/track?_export=pippo')
    assert res.status_code == 200
    assert_export(res, 'pippo')


def test_subresource(client):
    res = client.get('/album/5/track?_extended')
    assert res.status_code == 200

    data = res.get_json()['TrackList'][0]
    assert data['AlbumId'] == 5
    assert all(e in data.keys() for e in (
        "TrackId",
        "GenreId",
        "MediaTypeId",
        "Album",
        "Genre",
        "MediaType"
    ))
