"""Vigencia y ámbito de los avisos oficiales (docs/AVISOS-VIGENCIA-AMBITO.md). XML sintético: sin red ni claves."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import portinatx_degen as pd  # noqa: E402
import pirineo  # noqa: E402
import zone_sources as zs  # noqa: E402

UTC = timezone.utc
NOW = datetime(2026, 10, 17, 12, tzinfo=UTC)


def cap(zone='645301', emma='ES113', area='Ibiza y Formentera', onset='2026-10-17T09:00:00+02:00',
        expires='2026-10-18T14:59:59+02:00', effective='', sent='2026-10-17T09:16:09+00:00'):
    tags = ''.join(f'<{k}>{v}</{k}>' for k, v in (('effective', effective), ('onset', onset), ('expires', expires)) if v)
    geo = (f'<geocode><valueName>AEMET-Meteoalerta zona</valueName><value>{zone}</value></geocode>' if zone else '') + \
          (f'<geocode><valueName>EMMA_ID</valueName><value>{emma}</value></geocode>' if emma else '')
    return (f'<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2"><identifier>2.49.0.0.724.0.ES.X.{zone or "0"}PRP1'
            f'</identifier><sent>{sent}</sent><status>Actual</status><msgType>Alert</msgType><info>'
            f'<language>es-ES</language><event>Aviso de lluvias</event>{tags}<parameter><valueName>'
            f'AEMET-Meteoalerta nivel</valueName><value>naranja</value></parameter><area><areaDesc>{area}</areaDesc>'
            f'{geo}</area></info></alert>').encode()


# (nombre, CAP, zona pedida, nº avisos, activo_ahora, vigencia)
CASES = [
    ('caducado', cap(expires='2026-10-17T11:00:00+00:00'), '645301', 0, None, None),
    ('futuro', cap(onset='2026-10-18T09:00:00+02:00'), '645301', 1, False, 'DECLARADA'),
    ('en_vigor', cap(), '645301', 1, True, 'DECLARADA'),
    ('sin_expires', cap(expires=''), '645301', 1, True, 'SIN FIN DECLARADO'),
    # V-01: mientras el feed lo publique, un aviso sin fin sigue visible aunque su emisión sea antigua.
    ('sin_expires_sent_hace_25h', cap(expires='', sent='2026-10-16T11:00:00+00:00', onset='2026-10-16T12:00:00+00:00'),
     '645301', 1, True, 'SIN FIN DECLARADO'),
    ('sin_expires_sin_sent_onset_hace_30h', cap(expires='', sent='', onset='2026-10-16T06:00:00+00:00'),
     '645301', 1, True, 'SIN FIN DECLARADO'),
    ('sin_onset_con_effective', cap(onset='', effective='2026-10-17T10:00:00+00:00'), '645301', 1, True, 'DECLARADA'),
    # V-02/V-03: hora sin zona horaria = posiblemente activo, nunca descartado por leerla como UTC.
    ('sin_zona_horaria', cap(onset='2026-10-17T13:30:00'), '645301', 1, True, 'SIN HORARIO VERIFICABLE'),
    ('sin_zona_horaria_expires_pasado_en_utc', cap(onset='2026-10-16T09:00:00', expires='2026-10-17T11:30:00'),
     '645301', 1, True, 'SIN HORARIO VERIFICABLE'),
    ('sin_zona_horaria_expires_muy_pasado', cap(onset='2026-10-15T09:00:00', expires='2026-10-16T11:30:00'),
     '645301', 0, None, None),
    ('sin_onset_ni_effective', cap(onset=''), '645301', 1, True, 'SIN HORARIO VERIFICABLE'),
    ('zona_ajena_mallorca', cap(zone='645203', emma='ES872', area='Mallorca'), '645301', 0, None, None),
    ('ibiza_pedido_para_pirineo_691701', cap(), '691701', 0, None, None),
    ('ibiza_solo_emma_pedido_para_691701', cap(zone=''), '691701', 0, None, None),
    ('ibiza_solo_emma_pedido_para_ibiza', cap(zone=''), '645301', 1, True, 'DECLARADA'),
]


class CapVigenciaAmbito(unittest.TestCase):
    def test_casos(self):
        for name, blob, zone, n, active, vig in CASES:
            with self.subTest(name):
                w = pd.parse_cap_documents([blob], zone, NOW, 72)
                self.assertEqual(len(w), n)
                if n:
                    self.assertEqual(w[0]['activo_ahora'], active)
                    self.assertEqual(w[0]['vigencia'], vig)

    def test_sin_expires_documenta_retirada_prudente(self):
        w = pd.parse_cap_documents([cap(expires='')], '645301', NOW, 72)[0]
        self.assertEqual(w['expires'], '')
        # V-01: la retirada prudente cuenta desde la consulta, no desde sent.
        self.assertEqual(w['caduca_prudente'], (NOW + timedelta(hours=pd.CAP_SIN_FIN_H)).isoformat())

    def test_sin_zona_horaria_se_marca(self):
        self.assertEqual(pd.parse_cap_documents([cap(onset='2026-10-17T13:30:00')], '645301', NOW, 72)[0]['tz'],
                         'ASUMIDA_UTC')

    def test_mismo_plazo_en_motor_de_zonas(self):
        self.assertEqual(zs.NO_EXPIRES_MAX_H, pd.CAP_SIN_FIN_H)
        self.assertEqual(zs.TZ_SLACK_H, pd.CAP_TZ_HOLGURA_H)

    def test_aviso_sin_zona_horaria_cuenta_en_el_estado_oficial(self):
        w = pd.parse_cap_documents([cap(onset='2026-10-17T09:00:00', expires='2026-10-18T14:00:00')], '645301', NOW, 72)
        st = pd.official_state(pd.Channel('aviso_aemet_activo', 3, 'institutional'),
                               pd.Channel('aviso_aemet', 3, 'institutional'), w)
        self.assertEqual(st['vigente']['nivel'], 'naranja')
        self.assertEqual(st['vigentes'][0]['vigencia'], 'SIN HORARIO VERIFICABLE')
        src = pd.SourceResult(name='aemet_cap', status='ok', payload={'warnings': w})
        ch = pd.ch_institutional(src, active_only=True)
        self.assertEqual(ch.level, 2, 'el suelo institucional no se rebaja por una hora sin zona horaria')
        self.assertTrue(any('POSIBLEMENTE ACTIVO' in e for e in ch.evidence))


def atom(*entries):
    def entry(area, onset, expires, sent=''):
        t = ''.join(f'<cap:{k}>{v}</cap:{k}>' for k, v in (('sent', sent), ('onset', onset), ('expires', expires)) if v)
        return f'<entry><title>Yellow Snow Warning</title><cap:areaDesc>{area}</cap:areaDesc><cap:event>Nieve</cap:event>{t}</entry>'
    return ('<feed xmlns="http://www.w3.org/2005/Atom" xmlns:cap="urn:oasis:names:tc:emergency:cap:1.2">'
            + ''.join(entry(*e) for e in entries) + '</feed>').encode()


class PirineoAvisos(unittest.TestCase):
    def run_feeds(self, fake):
        with patch.object(pirineo.pd, 'http_get', fake), patch.object(pirineo.pd, 'now_utc', return_value=NOW):
            return pirineo.src_warnings()

    def test_ambito_y_fuente_caida(self):
        spain = atom(('Litoral sur de Girona', '2026-10-17T08:00:00+01:00', '2026-10-18T23:00:00+01:00'),
                     ('Prepirineo de Girona', '2026-10-17T08:00:00+01:00', '2026-10-18T23:00:00+01:00'),
                     ('Ibiza y Formentera', '2026-10-17T08:00:00+01:00', '2026-10-18T23:00:00+01:00'),
                     ('Pirineo de Lleida', '2026-10-17T08:00:00+01:00', '2026-10-18T23:00:00+01:00'),
                     ('Pirineo oscense', '2026-10-17T08:00:00+01:00', ''),
                     ('Pirineo de Gerona', '2026-10-17T08:00:00+01:00', '2026-10-18T23:00:00+01:00'),
                     ('PIRINEO DE GIRONA', '2026-10-17T08:00:00+01:00', '2026-10-18T23:00:00+01:00'))
        france = atom(('Pyre\u0301ne\u0301es-Orientales', '2026-10-17T08:00:00+01:00', '2026-10-18T23:00:00+01:00'),
                      ('Pyrénées Orientales', '2026-10-17T08:00:00+01:00', '2026-10-18T23:00:00+01:00'),
                      ('Pyrénées-Atlantiques', '2026-10-17T08:00:00+01:00', '2026-10-18T23:00:00+01:00'))

        def fake(url, *a, **k):
            if url.endswith('france'):
                raise OSError('offline')
            return spain if url.endswith('spain') else b'<feed></feed>'
        out = self.run_feeds(fake)
        areas = [w.get('area') for w in out if not w.get('error')]
        self.assertEqual(areas, ['Pirineo de Lleida', 'Pirineo oscense', 'Pirineo de Gerona', 'PIRINEO DE GIRONA'])
        # V-04: NFD (tildes descompuestas) y espacio en lugar de guion.
        fr = self.run_feeds(lambda url, *a, **k: france if url.endswith('france') else b'<feed></feed>')
        self.assertEqual([w['area'] for w in fr], ['Pyre\u0301ne\u0301es-Orientales', 'Pyrénées Orientales'])
        self.assertEqual([w['pais'] for w in out if w.get('error')], ['france'])
        sin_fin = [w for w in out if w.get('area') == 'Pirineo oscense'][0]
        self.assertEqual(sin_fin['vigencia'], 'SIN FIN DECLARADO')
        cob = {p: 'error' if any(w.get('pais') == p and w.get('error') for w in out) else 'ok' for p in pirineo.WARN_AREAS}
        self.assertEqual(cob['france'], 'error')
        estado = pirineo.warn_coverage_status(cob)
        self.assertTrue(estado.startswith('parcial') and 'Francia' in estado)
        self.assertFalse(estado.startswith('ok'), 'una fuente caída no puede certificar «sin avisos»')

    def test_estado_de_cobertura(self):
        for name, cob, prefix in (('todas', {'spain': 'ok', 'france': 'ok', 'andorra': 'ok'}, 'ok'),
                                  ('ninguna', {'spain': 'error', 'france': 'error', 'andorra': 'error'}, 'error'),
                                  ('andorra_caida', {'spain': 'ok', 'france': 'ok', 'andorra': 'error'}, 'parcial')):
            with self.subTest(name):
                self.assertTrue(pirineo.warn_coverage_status(cob).startswith(prefix))

    def test_aemet_cap_de_ibiza_no_entra_en_zonas_del_pirineo(self):
        with patch.dict('os.environ', {'AEMET_API_KEY': 'x'}), \
             patch.object(pirineo.pd, '_aemet', return_value=cap()), \
             patch.object(pirineo.pd, 'now_utc', return_value=NOW):
            self.assertEqual(pirineo.src_aemet_cap(), [])


class MotorDeZonas(unittest.TestCase):
    def feed(self, extra):
        return {'xml': '<feed xmlns="http://www.w3.org/2005/Atom" xmlns:cap="urn:oasis:names:tc:emergency:cap:1.2">'
                       f'<updated>{NOW.isoformat()}</updated><entry><id>e</id><title>T</title>'
                       f'<cap:areaDesc>{extra[0]}</cap:areaDesc>{extra[1]}</entry></feed>'}

    def test_casos(self):
        on = f'<cap:onset>{(NOW - timedelta(hours=1)).isoformat()}</cap:onset>'
        sent = f'<cap:sent>{(NOW - timedelta(hours=2)).isoformat()}</cap:sent>'
        old = f'<cap:sent>{(NOW - timedelta(hours=30)).isoformat()}</cap:sent>'
        naive_on = f'<cap:onset>{(NOW - timedelta(hours=1)).replace(tzinfo=None).isoformat()}</cap:onset>'
        naive_ex = f'<cap:expires>{(NOW - timedelta(hours=1)).replace(tzinfo=None).isoformat()}</cap:expires>'
        ex = f'<cap:expires>{(NOW + timedelta(hours=1)).isoformat()}</cap:expires>'
        area = {'country': 'spain', 'areas': ['pirineo de girona', 'pirineo de gerona']}
        for name, extra, n, validity in (
                ('en_vigor', ('Pirineo de Girona', on + ex), 1, 'declared'),
                ('prepirineo_no_es_pirineo', ('Prepirineo de Girona', on + ex), 0, None),
                ('sin_expires', ('Pirineo de Girona', sent + on), 1, 'end-not-declared'),
                ('sin_expires_emision_antigua_sigue', ('Pirineo de Girona', old + on), 1, 'end-not-declared'),
                ('sin_zona_horaria', ('Pirineo de Girona', naive_on + naive_ex), 1, 'time-not-verifiable'),
                ('sin_onset_ni_effective', ('Pirineo de Girona', ex), 1, 'time-not-verifiable'),
                ('nfd_y_gerona', ('Pirineo de Gerona', on + ex), 1, 'declared')):
            with self.subTest(name):
                res = zs.warnings(self.feed(extra), area, NOW)
                rec = res['records']
                self.assertEqual(len(rec), n)
                if n:
                    self.assertEqual(rec[0]['validity'], validity)
                    if validity == 'time-not-verifiable':
                        self.assertEqual(rec[0]['state'], 'possibly-active')
                        self.assertEqual(res['unverifiable_time'], 1)
                    zs.validate_data('warnings', {'schema': 1, 'kind': 'warnings', 'records': rec})


if __name__ == '__main__':
    unittest.main()
