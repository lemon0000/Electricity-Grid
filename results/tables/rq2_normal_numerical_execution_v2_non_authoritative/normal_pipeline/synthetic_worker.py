import sys
sys.path.insert(0, 'D:\\CUHKSZ\\Research Project\\electricity-grid')

import json
from copy import deepcopy
from pathlib import Path
from src.rq2_joint_deliverability_boundary_v1 import normal_worker as codec
from src.rq2_joint_deliverability_boundary_v1 import source_normal as source
from src.rq2_joint_deliverability_boundary_v1 import pair_normal_stream as pair
from src.rq2_joint_deliverability_boundary_v1 import normal_numerical_worker_v2 as worker
context=json.loads(Path(sys.argv.pop(1)).read_text(encoding='utf-8'))
inputs=codec._decode(context['inputs'])
source.RTS_GMLC_MANIFEST_SHA256=inputs.carry.identity.source_sha256
source.verify_sha256_manifest=lambda root: True
source.load_rts_gmlc_chronological_data=lambda root: inputs.data
pair.source_pair.prepare_source_pair=lambda *a,**k:deepcopy(context['pair'])
pair.source_window.load_source_window=lambda *a,**k:deepcopy(context['window'])
pair.source_window.audit._load_config=lambda *a:{'inputs':{'power':{}}}
pair.source_window.audit._verify_package=lambda *a:(None,{'grid_source_manifest_sha256':inputs.carry.identity.source_sha256})
pair.source_window.audit._verify_hash=lambda *a:None
worker.main()
