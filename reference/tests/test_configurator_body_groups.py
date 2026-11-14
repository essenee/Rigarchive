from django.test import TestCase
from reference.models import Manufacturer, VehicleModel, Generation, VehicleDefinition, FactoryBodyConfiguration
from reference.services import get_generation_hub_context
from .test_experimental_hub import ConfiguratorParser


class ConfiguratorBodyGroupTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        maker = Manufacturer.objects.create(name='Jeep')
        model = VehicleModel.objects.create(manufacturer=maker, name='Wrangler')
        cls.gen = Generation.objects.create(vehicle_model=model, name='JL', start_year=2018)
        cls.bodies = {door: FactoryBodyConfiguration.objects.create(generation=cls.gen, door_configuration=door)
                      for door in ('two-door','four-door')}
        cls.rows = []
        for trim in ('Willys','Rubicon'):
            for door, body in cls.bodies.items():
                for engine in ('2.0L I4 Turbo','3.6L V6 ESS'):
                    cls.rows.append(VehicleDefinition.objects.create(generation=cls.gen, model_year=2024,
                        trim_name=trim, factory_body_configuration=body, engine_name=engine, drivetrain='4WD',
                        market='US', slug=f'{trim.lower()}-{door}-{engine[:3].replace(".", "")}'))
        cls.sport = VehicleDefinition.objects.create(generation=cls.gen, model_year=2024,trim_name='Sport',
            factory_body_configuration=cls.bodies['four-door'], engine_name='2.0L I4 Turbo',drivetrain='4WD')

    def context(self, **params):
        return get_generation_hub_context(self.gen, model_year='2024', **params)

    def test_four_option_willys_is_split_into_two_exact_groups(self):
        context = self.context()
        groups = [g for g in context['available_trim_groups'] if g['trim']=='Willys']
        self.assertEqual({g['label'] for g in groups}, {'Willys · 2-Door','Willys · 4-Door'})
        for group in groups:
            selected = self.context(trim_name=group['key'])
            choices = selected['configuration_browser_choices']
            self.assertEqual(len(choices), 2)
            self.assertEqual({v.factory_body_configuration_id for v in choices},{group['body'].pk})
            self.assertEqual({v.trim_name for v in choices},{'Willys'})
            self.assertEqual({v.engine_name for v in choices},{'2.0L I4 Turbo','3.6L V6 ESS'})
            for v in choices:
                self.assertNotIn('US',v.choice_label)
                self.assertNotIn(v.slug,v.choice_label)
                self.assertNotIn('Door',v.choice_label)

    def test_other_trim_and_no_cartesian_groups(self):
        groups = self.context()['available_trim_groups']
        self.assertEqual(len([g for g in groups if g['trim']=='Rubicon']),2)
        self.assertEqual([g['label'] for g in groups if g['trim']=='Sport'],['Sport · 4-Door'])
        self.assertEqual(sum(len(g['pks']) for g in groups),9)
        self.assertEqual(set(VehicleDefinition.objects.values_list('trim_name',flat=True)),{'Sport','Willys','Rubicon'})

    def test_rendered_links_select_body_and_preserve_specs_destinations(self):
        response = self.client.get(self.gen.get_absolute_url(), {'year':2024})
        page = ConfiguratorParser(response.content.decode())
        from urllib.parse import urlsplit,parse_qs
        links = [l for l in page.links if 'trim-button' in l['attrs'].get('class','').split() and 'Willys' in l['text']]
        self.assertEqual(len(links),2)
        for link in links:
            params=parse_qs(urlsplit(link['attrs']['href']).query)
            result=self.client.get(self.gen.get_absolute_url(),params)
            chosen=result.context['configuration_browser_choices']
            self.assertEqual(len(chosen),2)
            parser=ConfiguratorParser(result.content.decode())
            specs=[l['attrs']['href'] for l in parser.links if l['attrs'].get('class')=='configuration-specs-link']
            self.assertEqual(set(specs),{v.get_absolute_url() for v in chosen})
            for url in specs:self.assertEqual(self.client.get(url).status_code,200)

    def test_exact_configuration_syncs_body_group_and_keeps_siblings(self):
        row=self.rows[0]
        c=get_generation_hub_context(self.gen,config_slug=row.slug)
        self.assertEqual(c['selected_config'],row)
        self.assertEqual({v.factory_body_configuration_id for v in c['configuration_browser_choices']},{row.factory_body_configuration_id})
        self.assertEqual(len(c['configuration_browser_choices']),2)

    def test_absent_trim_uses_body_without_inventing_marketed_trim(self):
        for body in self.bodies.values():
            VehicleDefinition.objects.create(generation=self.gen,model_year=2025,trim_name='',
                factory_body_configuration=body,engine_name='Engine',drivetrain='4WD',slug='unnamed-'+body.door_configuration)
        c=get_generation_hub_context(self.gen,model_year='2025')
        self.assertEqual({g['label'] for g in c['available_trim_groups']},{'2-Door','4-Door'})
        for group in c['available_trim_groups']:
            selected=get_generation_hub_context(self.gen,model_year='2025',trim_name=group['key'])
            self.assertEqual(len(selected['configuration_browser_choices']),1)
            self.assertEqual(selected['configuration_browser_choices'][0].trim_name,'')
