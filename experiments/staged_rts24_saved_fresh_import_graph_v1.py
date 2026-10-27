"""Static local-import inventory; no project module is imported or executed."""
import ast
from hashlib import sha256
from pathlib import Path

ROOT=Path(__file__).absolute().parents[1]
FORBIDDEN={'Highs','SolverFactory','ConcreteModel','AbstractModel','solve','optimize','build_model','create_model','create_session','begin_step','commit_step','replay','hold','capture','Popen','check_output','check_call','system','urlopen','exec','eval'}
# Reviewed local bytes and exact import-time calls. Any source or call change is rejected.
ADMITTED_INVENTORY={
    'src':{"import_time_calls":[],"path":"src/__init__.py","pin":{"bytes":38,"sha256":"ad4caa31a8bd5d534f5c65b38b67a393b740a5efd947988f47e1b55642c4cfc0"}},
    'src.evaluation':{"import_time_calls":[],"path":"src/evaluation/__init__.py","pin":{"bytes":3086,"sha256":"8b3883bd1641934074029b573735d5b0ac099ce0e42bb46b629becb0ce0137a9"}},
    'src.evaluation.capacity_metrics':{"import_time_calls":[{"callee":"dataclasses.dataclass","line":19},{"callee":"dataclasses.dataclass","line":29}],"path":"src/evaluation/capacity_metrics.py","pin":{"bytes":6023,"sha256":"272e876371c28d5f8ebd0396ebb9aaa43aef9e632b370322d9d3213203204d97"}},
    'src.evaluation.chronology_inputs':{"import_time_calls":[{"callee":"dataclasses.dataclass","line":51},{"callee":"dataclasses.dataclass","line":60},{"callee":"dataclasses.dataclass","line":68},{"callee":"dataclasses.dataclass","line":79},{"callee":"dataclasses.dataclass","line":88},{"callee":"dataclasses.dataclass","line":99}],"path":"src/evaluation/chronology_inputs.py","pin":{"bytes":16345,"sha256":"ef838c637b071ac89fffcdb5be9c9e7bc2d3fc75e1edf8172851b212e7c37c6b"}},
    'src.evaluation.economic_holdout':{"import_time_calls":[{"callee":"dataclasses.dataclass","line":93},{"callee":"dataclasses.dataclass","line":117},{"callee":"dataclasses.dataclass","line":138},{"callee":"dataclasses.dataclass","line":162}],"path":"src/evaluation/economic_holdout.py","pin":{"bytes":22180,"sha256":"147ec14fa2201d542c053de439a3303b4a7dd66385ddaff4bae9d5f60aadf939"}},
    'src.evaluation.flexibility_envelope':{"import_time_calls":[{"callee":"dataclasses.dataclass","line":12},{"callee":"dataclasses.dataclass","line":29},{"callee":"dataclasses.field","line":45},{"callee":"dataclasses.field","line":46},{"callee":"dataclasses.dataclass","line":52}],"path":"src/evaluation/flexibility_envelope.py","pin":{"bytes":21413,"sha256":"db007a9ac1fdd94779b734c6d39e841302f01a1ef49a121d2c00e0d0a996cd40"}},
    'src.evaluation.service_risk':{"import_time_calls":[{"callee":"dataclasses.dataclass","line":51},{"callee":"dataclasses.dataclass","line":71},{"callee":"dataclasses.dataclass","line":91}],"path":"src/evaluation/service_risk.py","pin":{"bytes":9655,"sha256":"67207f159297f7f4b6b02be61ab6df39c1832401ddb60bdc082abd4e99728989"}},
    'src.evaluation.stochastic_policy':{"import_time_calls":[{"callee":"<computed>.resolve","line":18},{"callee":"pathlib.Path","line":18},{"callee":"dataclasses.dataclass","line":45},{"callee":"dataclasses.dataclass","line":52},{"callee":"dataclasses.dataclass","line":59},{"callee":"dataclasses.dataclass","line":67},{"callee":"dataclasses.dataclass","line":77},{"callee":"dataclasses.dataclass","line":87},{"callee":"dataclasses.dataclass","line":104}],"path":"src/evaluation/stochastic_policy.py","pin":{"bytes":26253,"sha256":"dadf6ab1144fb84ca9985e56211b6d78e1d085438c26ec13217410cab5873225"}},
    'src.grid':{"import_time_calls":[],"path":"src/grid/__init__.py","pin":{"bytes":4412,"sha256":"b2490e8dfc9a5727c475cdca757eeb7606bb1318993dd3d8b14240dbe94467ef"}},
    'src.grid.ac_case':{"import_time_calls":[],"path":"src/grid/ac_case.py","pin":{"bytes":5231,"sha256":"d0c8c8b8d37480a87edc17a3af54b62663dec6e8b9d56ee03e235bae6bb2bb91"}},
    'src.grid.ac_restoration':{"import_time_calls":[{"callee":"dataclasses.dataclass","line":32}],"path":"src/grid/ac_restoration.py","pin":{"bytes":16475,"sha256":"59ba8af7047048e739f96c094373258bdb2548a6c2003a24939f2f3dfb5e0b74"}},
    'src.grid.ac_validation':{"import_time_calls":[{"callee":"dataclasses.dataclass","line":28}],"path":"src/grid/ac_validation.py","pin":{"bytes":7527,"sha256":"7e3488f966c979e103e436971b10996281c77e8c3a505e9103118baf3caf8a71"}},
    'src.grid.chronological_dispatch':{"import_time_calls":[{"callee":"dataclasses.dataclass","line":22},{"callee":"dataclasses.dataclass","line":54}],"path":"src/grid/chronological_dispatch.py","pin":{"bytes":24444,"sha256":"71d6c1da0e72942512810c651619c5cd73e915c3ac6d0d52684476d6133658ec"}},
    'src.grid.contingency':{"import_time_calls":[{"callee":"dataclasses.dataclass","line":12},{"callee":"dataclasses.dataclass","line":23}],"path":"src/grid/contingency.py","pin":{"bytes":6404,"sha256":"7a08c582fe7113b8a43355ff4ab888dd6a334fb2c0e79d5da8cb7f03acfd03fb"}},
    'src.grid.dc_opf':{"import_time_calls":[{"callee":"dataclasses.dataclass","line":25}],"path":"src/grid/dc_opf.py","pin":{"bytes":11996,"sha256":"9e118d7e8c59e269274749a144654ea5a400e35c6b1cb371870329ff2601e827"}},
    'src.grid.network_grid_need':{"import_time_calls":[{"callee":"dataclasses.dataclass","line":68},{"callee":"dataclasses.dataclass","line":85},{"callee":"dataclasses.dataclass","line":107},{"callee":"dataclasses.dataclass","line":130}],"path":"src/grid/network_grid_need.py","pin":{"bytes":37254,"sha256":"ca4ae719c8e1c96d398af6912994937272e31f4a29f7d485c74e0836d2199170"}},
    'src.grid.rts24':{"import_time_calls":[{"callee":"dataclasses.dataclass","line":33},{"callee":"dataclasses.dataclass","line":39},{"callee":"dataclasses.dataclass","line":53},{"callee":"dataclasses.dataclass","line":81}],"path":"src/grid/rts24.py","pin":{"bytes":6109,"sha256":"8c876b13fdc318ca98ab22309bae1aff0b8e56a12894f9aae98c84ed951eb8b5"}},
    'src.grid.rts_gmlc':{"import_time_calls":[{"callee":"frozenset","line":22},{"callee":"dataclasses.dataclass","line":28},{"callee":"dataclasses.dataclass","line":38},{"callee":"dataclasses.dataclass","line":44},{"callee":"dataclasses.dataclass","line":54},{"callee":"dataclasses.dataclass","line":68},{"callee":"dataclasses.dataclass","line":79},{"callee":"dataclasses.dataclass","line":112},{"callee":"dataclasses.dataclass","line":121},{"callee":"dataclasses.dataclass","line":132}],"path":"src/grid/rts_gmlc.py","pin":{"bytes":36900,"sha256":"4180ab5ce86eb34a9de9e058ff9c56275ace3a6ffab06dbb464d93ef23382448"}},
    'src.grid.rts_gmlc_scuc':{"import_time_calls":[{"callee":"frozenset","line":40},{"callee":"dataclasses.dataclass","line":55},{"callee":"dataclasses.dataclass","line":64},{"callee":"dataclasses.dataclass","line":73},{"callee":"dataclasses.dataclass","line":81},{"callee":"dataclasses.dataclass","line":89},{"callee":"dataclasses.dataclass","line":106},{"callee":"dataclasses.dataclass","line":115},{"callee":"dataclasses.dataclass","line":129},{"callee":"dataclasses.dataclass","line":150},{"callee":"dataclasses.dataclass","line":170}],"path":"src/grid/rts_gmlc_scuc.py","pin":{"bytes":82493,"sha256":"1101b21cbdab0cdacd6755578208ce7d28cd3e6e04f932d397119a4dde2b6cfe"}},
    'src.grid.scopf':{"import_time_calls":[{"callee":"dataclasses.dataclass","line":27},{"callee":"dataclasses.dataclass","line":38}],"path":"src/grid/scopf.py","pin":{"bytes":18944,"sha256":"cdd456ace5f704f31a80fab1c95dba272810cc815ffb6a4c71516e079982eb84"}},
    'src.models':{"import_time_calls":[],"path":"src/models/__init__.py","pin":{"bytes":1911,"sha256":"650c01ec0ee710bfb257114d761ebe173f2c4460aa1a28c1467c3cd2d257b391"}},
    'src.models.deterministic_baselines':{"import_time_calls":[{"callee":"frozenset","line":59},{"callee":"dataclasses.dataclass","line":74},{"callee":"dataclasses.dataclass","line":102},{"callee":"dataclasses.dataclass","line":118},{"callee":"frozenset","line":165}],"path":"src/models/deterministic_baselines.py","pin":{"bytes":49997,"sha256":"d7a4da3255e1f6fb523e91e3cb0c62b636c6fdc135cd92819c91a31bb5d4e94e"}},
    'src.models.deterministic_expansion':{"import_time_calls":[{"callee":"dataclasses.dataclass","line":38},{"callee":"dataclasses.dataclass","line":47},{"callee":"dataclasses.dataclass","line":54},{"callee":"dataclasses.dataclass","line":67}],"path":"src/models/deterministic_expansion.py","pin":{"bytes":43427,"sha256":"502de5b083b2a89f1a394cff69177da37f13eacc8494a5d1df67bda8b753f80c"}},
    'src.models.deterministic_fx':{"import_time_calls":[{"callee":"dataclasses.dataclass","line":51},{"callee":"dataclasses.dataclass","line":61},{"callee":"dataclasses.dataclass","line":69},{"callee":"dataclasses.dataclass","line":78},{"callee":"dataclasses.dataclass","line":109}],"path":"src/models/deterministic_fx.py","pin":{"bytes":53270,"sha256":"5b50e25d88309568d0f3c76139f27e4c82031c0757018c44c6afa8c6b7239158"}},
    'src.models.economic_stochastic':{"import_time_calls":[{"callee":"dataclasses.dataclass","line":110},{"callee":"dataclasses.dataclass","line":130},{"callee":"dataclasses.dataclass","line":161},{"callee":"dataclasses.dataclass","line":172}],"path":"src/models/economic_stochastic.py","pin":{"bytes":21459,"sha256":"767a8655e911188cbc716adf907734d6042b922793f8b87a9308d64b6fb35c39"}},
    'src.models.rq2_network_grid_need':{"import_time_calls":[{"callee":"dataclasses.dataclass","line":22},{"callee":"dataclasses.dataclass","line":33}],"path":"src/models/rq2_network_grid_need.py","pin":{"bytes":7641,"sha256":"30bcfc45affbd1ce582aee5fca1ec8bfc79e16803cf95ee10473efefc6c1e688"}},
    'src.models.stochastic_baselines':{"import_time_calls":[{"callee":"frozenset","line":66},{"callee":"dataclasses.dataclass","line":193},{"callee":"dataclasses.dataclass","line":231}],"path":"src/models/stochastic_baselines.py","pin":{"bytes":74189,"sha256":"b84fe3bdea320794551d773007a69757e022f43b358943e8832e32e62d11bbf2"}},
    'src.rq2_joint_deliverability_boundary_v1':{"import_time_calls":[],"path":"src/rq2_joint_deliverability_boundary_v1/__init__.py","pin":{"bytes":74,"sha256":"23dcf6e6cc99671101ae4e4c05602f5345aae114aa011b89511839c208a33856"}},
    'src.rq2_joint_deliverability_boundary_v1.debt_cohorts':{"import_time_calls":[{"callee":"dataclasses.dataclass","line":21},{"callee":"dataclasses.dataclass","line":51}],"path":"src/rq2_joint_deliverability_boundary_v1/debt_cohorts.py","pin":{"bytes":6483,"sha256":"d10497c1e6ab5ff573dec8d938b5407a7e28277551b37a1e0d7f79b4241adaab"}},
    'src.rq2_joint_deliverability_boundary_v1.normal_process':{"import_time_calls":[{"callee":"dataclasses.dataclass","line":109}],"path":"src/rq2_joint_deliverability_boundary_v1/normal_process.py","pin":{"bytes":13559,"sha256":"ffc487c05c72d00a7c2e8d7515a29f16a3d0c8ac3f0efa6cdba36bbcea34d44f"}},
    'src.scenarios':{"import_time_calls":[],"path":"src/scenarios/__init__.py","pin":{"bytes":2956,"sha256":"bb02b61cca991980b994a322c25ada4f3eff2028bd6d6552f44f63346d88e599"}},
    'src.scenarios.common_input_signature':{"import_time_calls":[],"path":"src/scenarios/common_input_signature.py","pin":{"bytes":5673,"sha256":"fe7f80d40df987d2b739a756b7a12fb7514e24c4e873f8b36e6aa0e0a3d6655f"}},
    'src.scenarios.frozen_tree':{"import_time_calls":[{"callee":"dataclasses.dataclass","line":73},{"callee":"dataclasses.dataclass","line":82},{"callee":"dataclasses.dataclass","line":89},{"callee":"dataclasses.dataclass","line":97},{"callee":"dataclasses.dataclass","line":106},{"callee":"dataclasses.dataclass","line":112},{"callee":"dataclasses.dataclass","line":121},{"callee":"dataclasses.dataclass","line":128}],"path":"src/scenarios/frozen_tree.py","pin":{"bytes":33159,"sha256":"9bcafccaee051474d31a491f4f042d886bb2746e6d3f455f6755571da9f1729f"}},
    'src.scenarios.rts_gmlc_cfe_deficit':{"import_time_calls":[{"callee":"frozenset","line":15},{"callee":"dataclasses.dataclass","line":40},{"callee":"dataclasses.dataclass","line":53},{"callee":"dataclasses.dataclass","line":65}],"path":"src/scenarios/rts_gmlc_cfe_deficit.py","pin":{"bytes":10745,"sha256":"27944b3ac9e30173f1b6d9708d2b8c7d15875ec73d187d2500028f4af837d1e6"}},
    'src.scenarios.scenario_reduction':{"import_time_calls":[{"callee":"dataclasses.dataclass","line":79},{"callee":"dataclasses.field","line":94}],"path":"src/scenarios/scenario_reduction.py","pin":{"bytes":11429,"sha256":"7bcd4340cc5ef8a3302884b56e6f8fba89eb8b005c83fa8cc5e00f8e93c38ec5"}},
    'src.scenarios.temporal_scenario_reduction':{"import_time_calls":[{"callee":"dataclasses.dataclass","line":27},{"callee":"dataclasses.field","line":32}],"path":"src/scenarios/temporal_scenario_reduction.py","pin":{"bytes":11620,"sha256":"2a1af9cb2483938480ca8e1cb4518c1d23fa1421daac1d5597b608018648ef2d"}},
    'src.scenarios.temporal_trace_scenario_generator':{"import_time_calls":[{"callee":"dataclasses.dataclass","line":27},{"callee":"dataclasses.dataclass","line":43},{"callee":"dataclasses.dataclass","line":62},{"callee":"dataclasses.field","line":67}],"path":"src/scenarios/temporal_trace_scenario_generator.py","pin":{"bytes":11035,"sha256":"8769588882099aace6d9c61faf51db4491920bad3610ac54097f7c7f941f5307"}},
    'src.scenarios.trace_scenario_generator':{"import_time_calls":[{"callee":"dataclasses.dataclass","line":121},{"callee":"dataclasses.dataclass","line":255},{"callee":"dataclasses.dataclass","line":278},{"callee":"dataclasses.field","line":285}],"path":"src/scenarios/trace_scenario_generator.py","pin":{"bytes":25147,"sha256":"01117f70b0cae4eed2d40e50e9981dc035ad7109b7f02b32d57f6d4bc3dc325b"}},
    'src.solvers':{"import_time_calls":[],"path":"src/solvers/__init__.py","pin":{"bytes":334,"sha256":"eb3b5f0d9aea2b5b3316284f7c0baee4c6dffaa5779a14f833d9d279927189d8"}},
    'src.solvers.osqp_qp':{"import_time_calls":[{"callee":"dataclasses.dataclass","line":16},{"callee":"dataclasses.field","line":37},{"callee":"dataclasses.dataclass","line":99}],"path":"src/solvers/osqp_qp.py","pin":{"bytes":19477,"sha256":"b5f0c188da81d7f796f900d988b5f5ec7903e7680001e79f5bc3ba79cbafc526"}},
    'src.staged_deliverability_development_v1':{"import_time_calls":[{"callee":"fractions.Fraction","line":18},{"callee":"dataclasses.dataclass","line":42},{"callee":"dataclasses.dataclass","line":78},{"callee":"dataclasses.dataclass","line":108},{"callee":"dataclasses.dataclass","line":132}],"path":"src/staged_deliverability_development_v1.py","pin":{"bytes":19642,"sha256":"91bbc6aaaac458c8fcb23c11d830a98af99e1d50d42b3c0489246ec1922109e0"}},
    'src.staged_rts24_audit_v1':{"import_time_calls":[],"path":"src/staged_rts24_audit_v1.py","pin":{"bytes":13053,"sha256":"ac29e1fe38831b7f37fbd56ab7ceafc8d87a619c5c1ba929004f907e21aab911"}},
    'src.staged_rts24_causal_audit_v2':{"import_time_calls":[],"path":"src/staged_rts24_causal_audit_v2.py","pin":{"bytes":13435,"sha256":"3344d346efc62b1bef8cbeab470eb3696a9818c4f452465394ab33806baf28d3"}},
    'src.staged_rts24_causal_v1':{"import_time_calls":[{"callee":"fractions.Fraction","line":14},{"callee":"dataclasses.dataclass","line":17},{"callee":"dataclasses.dataclass","line":25},{"callee":"dataclasses.dataclass","line":33},{"callee":"dataclasses.dataclass","line":65},{"callee":"dataclasses.dataclass","line":81}],"path":"src/staged_rts24_causal_v1.py","pin":{"bytes":19309,"sha256":"12950e9f0ac321e7297b66aba42efb9e486e477869d767e40cd841665a7b0ead"}},
    'src.staged_rts24_causal_v2':{"import_time_calls":[],"path":"src/staged_rts24_causal_v2.py","pin":{"bytes":11081,"sha256":"7d22dba435d3e89bd3062a1bd687a6584bb7ddc29c88b6bd723fa357932d1859"}},
    'src.staged_rts24_child_optimality_v1':{"import_time_calls":[{"callee":"dataclasses.dataclass","line":11}],"path":"src/staged_rts24_child_optimality_v1.py","pin":{"bytes":8256,"sha256":"27071de638bceee8f6e0631ab44d8a9c3cebdba0c169ccd702c9c3392fcde543"}},
    'src.staged_rts24_development_v1':{"import_time_calls":[{"callee":"<computed>.resolve","line":14},{"callee":"pathlib.Path","line":14},{"callee":"dataclasses.dataclass","line":79},{"callee":"dataclasses.dataclass","line":86},{"callee":"dataclasses.dataclass","line":99},{"callee":"dataclasses.dataclass","line":220},{"callee":"fractions.Fraction","line":239},{"callee":"dataclasses.dataclass","line":284},{"callee":"dataclasses.dataclass","line":294},{"callee":"dataclasses.dataclass","line":306}],"path":"src/staged_rts24_development_v1.py","pin":{"bytes":26764,"sha256":"d0c61bda61bfe4d275d2230533f2ecd74fa4fbf480f358c819f8cb86e1ba7add"}},
    'src.staged_rts24_evidence_store_v1':{"import_time_calls":[{"callee":"re.compile","line":32},{"callee":"typing.get_type_hints","line":38},{"callee":"CLASSES.values","line":38},{"callee":"<computed>.update","line":39},{"callee":"<computed>.update","line":43}],"path":"src/staged_rts24_evidence_store_v1.py","pin":{"bytes":16709,"sha256":"54a23ba142d12abe0a394437cb6967b0029ed573eddff1b6efb7adbaca7883c6"}},
    'src.staged_rts24_highs_backend_v1':{"import_time_calls":[{"callee":"dict","line":19}],"path":"src/staged_rts24_highs_backend_v1.py","pin":{"bytes":14536,"sha256":"cae8e98941f6d813b96413d67b96acce263997d2197e63ad090cff8f061dbccf"}},
    'src.staged_rts24_journal_v2':{"import_time_calls":[{"callee":"<computed>.absolute","line":23},{"callee":"pathlib.Path","line":23},{"callee":"re.compile","line":42},{"callee":"dataclasses.dataclass","line":58},{"callee":"dataclasses.dataclass","line":76}],"path":"src/staged_rts24_journal_v2.py","pin":{"bytes":30876,"sha256":"5216b58cbaf1d2a2aa26ce00e71f3563bda793b9512dede023a013ef462bdb0e"}},
    'src.staged_rts24_numeric_interface_v1':{"import_time_calls":[{"callee":"dataclasses.dataclass","line":18},{"callee":"dataclasses.dataclass","line":28},{"callee":"dataclasses.dataclass","line":36},{"callee":"dataclasses.dataclass","line":44},{"callee":"dataclasses.dataclass","line":64}],"path":"src/staged_rts24_numeric_interface_v1.py","pin":{"bytes":14093,"sha256":"570cd1e52f5c78c1ee37f589fb28b646f4173dede32600ba3bff8ceeb447ec31"}},
    'src.staged_rts24_p2_outer_observation_v1':{"import_time_calls":[{"callee":"dict","line":10}],"path":"src/staged_rts24_p2_outer_observation_v1.py","pin":{"bytes":10412,"sha256":"8d80e035c2570d279360d67cf6bb93b125970fae81e5c638a396351f8dd78b91"}},
    'src.staged_rts24_p2_outer_observation_v2':{"import_time_calls":[],"path":"src/staged_rts24_p2_outer_observation_v2.py","pin":{"bytes":14886,"sha256":"256ed39e3efc36578a08f24bb39d7b14ca4b693dbcc94c1dec379fe125266f04"}},
    'src.staged_rts24_p2_package_check_v1':{"import_time_calls":[{"callee":"dict","line":15},{"callee":"dict","line":27},{"callee":"dict","line":28},{"callee":"dict","line":29},{"callee":"set","line":31},{"callee":"<computed>.split","line":31},{"callee":"set","line":32},{"callee":"<computed>.split","line":32}],"path":"src/staged_rts24_p2_package_check_v1.py","pin":{"bytes":50876,"sha256":"5794f8a35814cb5ad64fb38de2d8591e2e23e3bdb57921f0c84c853627466eb2"}},
    'src.staged_rts24_process_guard_v1':{"import_time_calls":[],"path":"src/staged_rts24_process_guard_v1.py","pin":{"bytes":12191,"sha256":"02b6098e9a5b2cb6c2b862c81b9a375ee631e7cbee5e409310905a3ef2512fc2"}},
    'src.staged_rts24_process_guard_v3':{"import_time_calls":[],"path":"src/staged_rts24_process_guard_v3.py","pin":{"bytes":6548,"sha256":"d3fe404aa7265c2a479423cd9991a54326c32e4d7b729bfff20f49fd1b2262c4"}},
    'src.staged_rts24_reference_queries_v1':{"import_time_calls":[],"path":"src/staged_rts24_reference_queries_v1.py","pin":{"bytes":2618,"sha256":"be02760eec2a0d010ec1a2187322edcca14af4774e7e6d0cbf4859a9375adb1a"}},
    'src.staged_rts24_saved_fresh_adoption_v1':{"import_time_calls":[{"callee":"tuple","line":19},{"callee":"sorted","line":19},{"callee":"set","line":19},{"callee":"tuple","line":22},{"callee":"sorted","line":22},{"callee":"set","line":22},{"callee":"tuple","line":27},{"callee":"<computed>.split","line":27},{"callee":"dict","line":30},{"callee":"dataclasses.dataclass","line":62}],"path":"src/staged_rts24_saved_fresh_adoption_v1.py","pin":{"bytes":17247,"sha256":"26b919e385f9d7042587db490dab694fc5bf1643665ab4bf94a1c9bac8087396"}},
    'src.staged_rts24_saved_point_replay_v1':{"import_time_calls":[{"callee":"<computed>.resolve","line":18},{"callee":"pathlib.Path","line":18},{"callee":"set","line":31},{"callee":"<computed>.split","line":31}],"path":"src/staged_rts24_saved_point_replay_v1.py","pin":{"bytes":16793,"sha256":"f9f723e89bb6513b4ba25c61b427f363652f2be78707d132511f6929f3df95ad"}},
    'src.staged_rts24_saved_prefix_replay_v1':{"import_time_calls":[],"path":"src/staged_rts24_saved_prefix_replay_v1.py","pin":{"bytes":11867,"sha256":"22bee015d89d818b8e76a5f2f44cf3b2618fffe7641e73461e4481bd80738a4c"}},
}

def validate_inventory(modules):
    assert type(modules) is dict and set(modules)==set(ADMITTED_INVENTORY)
    for name,row in modules.items():
        observed={key:row[key] for key in ('path','pin','import_time_calls')}
        assert observed==ADMITTED_INVENTORY[name],name
    return True

def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def inspect_imports():
    pending=['src.staged_rts24_saved_fresh_adoption_v1'];seen=set();rows={};external=set();total=0;violations=[]
    def locate(name):
        parts=name.split('.');base=ROOT.joinpath(*parts)
        for path in (base.with_suffix('.py'),base/'__init__.py'):
            if path.is_file():return path
        return None
    def label(node):
        if type(node) is ast.Name:return node.id
        if type(node) is ast.Attribute:return label(node.value)+'.'+node.attr
        return '<computed>'
    while pending:
        name=pending.pop()
        if name in seen:continue
        seen.add(name);path=locate(name)
        if path is None:external.add(name);continue
        assert len(rows)<256
        raw=path.read_bytes();total+=len(raw);assert total<=20*1024**2
        tree=ast.parse(raw);deps=set();calls=[];aliases={};main_guards=0
        package=name if path.name=='__init__.py' else name.rpartition('.')[0]
        def evaluate(node):
            nonlocal main_guards
            if type(node) is ast.If and type(node.test) is ast.Compare:
                t=node.test
                if type(t.left) is ast.Name and t.left.id=='__name__' and len(t.ops)==1 and type(t.ops[0]) is ast.Eq and len(t.comparators)==1 and type(t.comparators[0]) is ast.Constant and t.comparators[0].value=='__main__':
                    main_guards+=1
                    for item in node.orelse:evaluate(item)
                    return
            if type(node) in (ast.FunctionDef,ast.AsyncFunctionDef):
                for item in (*node.decorator_list,*node.args.defaults,*[v for v in node.args.kw_defaults if v is not None]):evaluate(item)
                return
            if type(node) is ast.Lambda:return
            if type(node) is ast.ClassDef:
                for item in (*node.decorator_list,*node.bases,*[k.value for k in node.keywords],*node.body):evaluate(item)
                return
            if type(node) is ast.Import:
                for item in node.names:
                    deps.add(item.name);aliases[item.asname or item.name.split('.')[0]]=item.name if item.asname else item.name.split('.')[0]
            elif type(node) is ast.ImportFrom:
                prefix=package.split('.') if package else []
                if node.level:prefix=prefix[:len(prefix)-node.level+1]
                else:prefix=[]
                base='.'.join((*prefix,*((node.module or '').split('.') if node.module else [])))
                if base:deps.add(base)
                for item in node.names:
                    full=base+'.'+item.name if base else item.name
                    aliases[item.asname or item.name]=full
                    if locate(full) is not None:deps.add(full)
            elif type(node) is ast.Call:
                fn=label(node.func);head,*tail=fn.split('.');resolved='.'.join((aliases.get(head,head),*tail))
                calls.append(dict(line=node.lineno,callee=resolved));assert len(calls)<=1024
                if resolved.rsplit('.',1)[-1] in FORBIDDEN:violations.append(dict(path=path.relative_to(ROOT).as_posix(),line=node.lineno,callee=resolved))
            for child in ast.iter_child_nodes(node):evaluate(child)
        for node in tree.body:evaluate(node)
        for dep in tuple(deps):
            for i in range(1,len(dep.split('.'))):
                parent='.'.join(dep.split('.')[:i])
                if locate(parent) is not None:deps.add(parent)
        rows[name]=dict(path=path.relative_to(ROOT).as_posix(),pin=pin(raw),dependencies=sorted(deps),import_time_calls=calls,main_guards_excluded=main_guards)
        pending.extend(sorted(deps-seen,reverse=True))
    assert not violations,violations
    validate_inventory(rows)
    return dict(module_count=len(rows),source_bytes=total,modules=rows,external_leaves=sorted(external),forbidden_direct_top_calls=violations,
        reviewed_local_inventory_matched=True,method='exact reviewed local source hashes and import-time calls; deferred bodies excluded',transitive_external_behavior_verified=False)
