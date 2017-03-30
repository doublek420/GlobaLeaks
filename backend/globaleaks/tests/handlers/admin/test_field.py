from globaleaks.tid import XTIDX
# -*- coding: utf-8 -*-
import copy

from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers import admin
from globaleaks.handlers.admin.context import create_context
from globaleaks.handlers.admin.field import create_field
from globaleaks.orm import transact
from globaleaks.rest import errors
from globaleaks.tests import helpers


@transact
def get_id_of_first_step_of_questionnaire(store, questionnaire_id):
    return store.find(models.Step, models.Step.questionnaire_id == questionnaire_id)[0].id


class TestFieldCreate(helpers.TestHandler):
        _handler = admin.field.FieldCollection

        @inlineCallbacks
        def test_post(self):
            """
            Attempt to create a new field via a post request.
            """
            values = helpers.get_dummy_field()
            values['instance'] = 'instance'
            context = yield create_context(XTIDX, self.dummyContext, 'en')
            values['step_id'] = yield get_id_of_first_step_of_questionnaire(context['questionnaire_id'])
            handler = self.request(values, role='admin')
            yield handler.post()
            self.assertEqual(len(self.responses), 1)

            resp = self.responses[0]
            self.assertIn('id', resp)
            self.assertNotEqual(resp.get('options'), None)

        @inlineCallbacks
        def test_post_create_from_template(self):
            """
            Attempt to create a new field from template via post request
            """
            values = helpers.get_dummy_field()
            values['instance'] = 'template'
            field_template = yield create_field(values, 'en')

            context = yield create_context(XTIDX, copy.deepcopy(self.dummyContext), 'en')

            values = helpers.get_dummy_field()
            values['instance'] = 'reference'
            values['template_id'] = field_template['id']
            values['step_id'] = yield get_id_of_first_step_of_questionnaire(context['questionnaire_id'])

            handler = self.request(values, role='admin')
            yield handler.post()
            self.assertEqual(len(self.responses), 1)

            resp = self.responses[0]
            self.assertIn('id', resp)
            self.assertNotEqual(resp.get('options'), None)


class TestFieldInstance(helpers.TestHandler):
        _handler = admin.field.FieldInstance

        @inlineCallbacks
        def test_get(self):
            """
            Create a new field, then get it back using the received id.
            """
            values = helpers.get_dummy_field()
            values['instance'] = 'instance'
            context = yield create_context(XTIDX, copy.deepcopy(self.dummyContext), 'en')
            values['step_id'] = yield get_id_of_first_step_of_questionnaire(context['questionnaire_id'])
            field = yield create_field(values, 'en')

            handler = self.request(role='admin')
            yield handler.get(field['id'])
            self.assertEqual(len(self.responses), 1)
            self.assertEqual(field['id'], self.responses[0]['id'])

        @inlineCallbacks
        def test_put(self):
            """
            Attempt to update a field, changing its type via a put request.
            """
            values = helpers.get_dummy_field()
            values['instance'] = 'instance'
            context = yield create_context(XTIDX, copy.deepcopy(self.dummyContext), 'en')
            values['step_id'] = yield get_id_of_first_step_of_questionnaire(context['questionnaire_id'])
            field = yield create_field(values, 'en')

            updated_sample_field = helpers.get_dummy_field()
            updated_sample_field['instance'] = 'instance'
            context = yield create_context(XTIDX, copy.deepcopy(self.dummyContext), 'en')
            updated_sample_field['step_id'] = yield get_id_of_first_step_of_questionnaire(context['questionnaire_id'])
            updated_sample_field.update(type='inputbox')
            handler = self.request(updated_sample_field, role='admin')
            yield handler.put(field['id'])
            self.assertEqual(len(self.responses), 1)
            self.assertEqual(field['id'], self.responses[0]['id'])
            self.assertEqual(self.responses[0]['type'], 'inputbox')

            wrong_sample_field = helpers.get_dummy_field()
            values['instance'] = 'instance'
            values['step_id'] = yield get_id_of_first_step_of_questionnaire(context['questionnaire_id'])
            wrong_sample_field.update(type='nonexistingfieldtype')
            handler = self.request(wrong_sample_field, role='admin')
            yield self.assertFailure(handler.put(field['id']), errors.InvalidInputFormat)

        @inlineCallbacks
        def test_delete(self):
            """
            Create a new field, then attempt to delete it.
            """
            values = helpers.get_dummy_field()
            values['instance'] = 'instance'
            context = yield create_context(XTIDX, copy.deepcopy(self.dummyContext), 'en')
            values['step_id'] = yield get_id_of_first_step_of_questionnaire(context['questionnaire_id'])
            field = yield create_field(values, 'en')

            handler = self.request(role='admin')
            yield handler.delete(field['id'])
            self.assertEqual(handler.get_status(), 200)
            # second deletion operation should fail
            yield self.assertFailure(handler.delete(field['id']), errors.FieldIdNotFound)


class TestFieldTemplateInstance(helpers.TestHandlerWithPopulatedDB):
        _handler = admin.field.FieldTemplateInstance

        @inlineCallbacks
        def test_get(self):
            """
            Create a new field, the get it back using the receieved id.
            """
            values = helpers.get_dummy_field()
            values['instance'] = 'template'
            field = yield create_field(values, 'en')

            handler = self.request(role='admin')
            yield handler.get(field['id'])
            self.assertEqual(len(self.responses), 1)
            self.assertEqual(field['id'], self.responses[0]['id'])

        @inlineCallbacks
        def test_put(self):
            """
            Attempt to update a field, changing its type via a put request.
            """
            values = helpers.get_dummy_field()
            values['instance'] = 'template'
            field = yield create_field(values, 'en')

            updated_sample_field = helpers.get_dummy_field()
            updated_sample_field['instance'] = 'template'
            updated_sample_field['type'] ='inputbox'
            handler = self.request(updated_sample_field, role='admin')
            yield handler.put(field['id'])
            self.assertEqual(len(self.responses), 1)
            self.assertEqual(field['id'], self.responses[0]['id'])
            self.assertEqual(self.responses[0]['type'], 'inputbox')

            wrong_sample_field = helpers.get_dummy_field()
            wrong_sample_field.update(type='nonexistingfieldtype')
            handler = self.request(wrong_sample_field, role='admin')
            yield self.assertFailure(handler.put(field['id']), errors.InvalidInputFormat)

        @inlineCallbacks
        def test_delete(self):
            """
            Create a new field template, then attempt to delete it.
            """
            values = helpers.get_dummy_field()
            values['instance'] = 'template'
            field = yield create_field(values, 'en')

            handler = self.request(role='admin')
            yield handler.delete(field['id'])
            self.assertEqual(handler.get_status(), 200)
            # second deletion operation should fail
            yield self.assertFailure(handler.delete(field['id']), errors.FieldIdNotFound)


class TestFieldTemplatesCollection(helpers.TestHandlerWithPopulatedDB):
        _handler = admin.field.FieldTemplatesCollection

        @inlineCallbacks
        def test_get(self):
            """
            Retrieve a list of all fields, and verify that they do exist in the
            database.
            """
            n = 3
            ids = []
            for i in range(n):
                values = helpers.get_dummy_field()
                values['instance'] = 'template'
                handler = self.request(values, role='admin')
                yield handler.post()
                ids.append(self.responses[i]['id'])

            self.responses = []
            handler = self.request(role='admin')
            yield handler.get()
            fields, = self.responses

            check_ids = [field.get('id') for field in fields]
            self.assertGreater(len(fields), n)
            self.assertNotIn(None, ids)

            for x in ids:
                self.assertIn(x, check_ids)

            # check tha childrens are not present in the list
            # as the list should contain only parents fields
            for field in fields:
                for child in field['children']:
                    self.assertNotIn(child, ids)

        @inlineCallbacks
        def test_post(self):
            """
            Attempt to create a new field via a post request.
            """
            values = helpers.get_dummy_field()
            values['instance'] = 'template'
            handler = self.request(values, role='admin')
            yield handler.post()
            self.assertEqual(len(self.responses), 1)

            resp = self.responses[0]
            self.assertIn('id', resp)
            self.assertNotEqual(resp.get('options'), None)
