"""Public schema identity stays fixed when Python packages move."""
from copy import deepcopy
import unittest

from app.raid_rooms.contracts.schema_ids import preserve


class SchemaIdentityTests(unittest.TestCase):
    current = 'app__game_accounts__schemas__schemas__Summary'
    published = 'app__game_accounts__schemas__Summary'

    def document(self):
        return {'components': {'schemas': {
            self.current: {'type': 'object'},
            'Envelope': {'properties': {'value': {'$ref': '#/components/schemas/' + self.current}}},
        }}}

    def test_keys_and_references_keep_published_identity(self):
        value = preserve(self.document())
        definitions = value['components']['schemas']
        self.assertNotIn(self.current, definitions)
        self.assertIn(self.published, definitions)
        self.assertEqual(definitions['Envelope']['properties']['value']['$ref'], '#/components/schemas/' + self.published)

    def test_discriminator_mapping_is_updated(self):
        value = self.document()
        value['components']['schemas']['Envelope']['discriminator'] = {
            'propertyName': 'kind', 'mapping': {'one': '#/components/schemas/' + self.current, 'two': self.current}}
        result = preserve(value)['components']['schemas']['Envelope']['discriminator']['mapping']
        self.assertEqual(result, {'one': '#/components/schemas/' + self.published, 'two': self.published})

    def test_examples_and_defaults_are_user_values(self):
        value = self.document()
        literal = {'$ref': '#/components/schemas/' + self.current}
        envelope = value['components']['schemas']['Envelope']
        for key in ('example', 'examples', 'default', 'const', 'enum'):
            envelope[key] = deepcopy(literal)
        result = preserve(value)['components']['schemas']['Envelope']
        for key in ('example', 'examples', 'default', 'const', 'enum'):
            self.assertEqual(result[key], literal)

    def test_properties_named_like_metadata_are_still_schemas(self):
        value = self.document()
        value['components']['schemas']['Envelope']['properties']['examples'] = {'$ref': '#/components/schemas/' + self.current}
        result = preserve(value)['components']['schemas']['Envelope']['properties']['examples']
        self.assertEqual(result['$ref'], '#/components/schemas/' + self.published)

    def test_collision_fails_without_overwriting_definition(self):
        value = self.document()
        value['components']['schemas'][self.published] = {'type': 'string'}
        original = deepcopy(value)
        with self.assertRaisesRegex(ValueError, 'collision'):
            preserve(value)
        self.assertEqual(value, original)

    def test_unresolved_schema_reference_is_rejected(self):
        value = self.document()
        value['components']['schemas']['Envelope']['properties']['value']['$ref'] = '#/components/schemas/Missing'
        with self.assertRaisesRegex(ValueError, 'Unresolved'):
            preserve(value)

    def test_repeated_generation_is_idempotent(self):
        value = preserve(self.document())
        original = deepcopy(value)
        self.assertIs(preserve(value), value)
        self.assertEqual(value, original)
