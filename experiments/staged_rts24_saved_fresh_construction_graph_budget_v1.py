"""Static call accounting for frozen successor code; not wall/RSS admission."""
STAGES=('loader_ready','before_adapter_import','adapter_import_returned','after_adapter_import_attempt',
    'before_machinery_authentication','machinery_authenticated','before_source_bytes','after_source_bytes',
    'before_adapter_roots','after_adapter_roots','before_final_source_bookend','after_final_source_bookend',
    'before_retention','after_retention','before_boundary_close','after_boundary_close','before_profile','after_profile',
    'before_finish_import','after_finish_import','before_final_runtime_close','after_final_runtime_close')
INTERVALS={'<before_loader_ready>':['namespace']*19,'loader_ready':['namespace']*2,
    'after_adapter_import_attempt':['namespace']*5,'before_source_bytes':['namespace'],
    'before_adapter_roots':['adapter'],'before_boundary_close':['adapter']*2,'before_profile':['adapter'],
    'before_finish_import':['namespace','adapter','adapter','namespace','adapter','namespace','adapter'],
    'after_finish_import':['namespace','adapter'],'before_final_runtime_close':['namespace','adapter','namespace']}
PRODUCER_OPERATIONS=(('prepare',5,5,5,2),('run_G0',8,8,8,8),('G2',7,7,7,7),('G3',7,7,7,7),('close',7,8,7,4))


def contract():
    return dict(schema='staged_saved_F_construction_graph_contract_v1',calls=43,
        kinds=dict(namespace=33,adapter=10),intervals={key:list(value) for key,value in INTERVALS.items()})


def current():
    values=[kind for row in INTERVALS.values() for kind in row]
    assert len(values)==43 and values.count('namespace')==33 and values.count('adapter')==10
    assert sum(row[1] for row in PRODUCER_OPERATIONS)==34
    assert sum(row[2] for row in PRODUCER_OPERATIONS)==35 and sum(row[3] for row in PRODUCER_OPERATIONS)==34
    assert sum(row[4] for row in PRODUCER_OPERATIONS)==28
    return None,dict(schema='staged_saved_F_static_graph_budget_v1',authority='DRAFT_NONAUTHORITATIVE',
        construction=contract(),post_return_counts=dict(authenticate=1,finder_check=16,adapter_check=9,profile=2),
        source_bookends=7,producer_operations=PRODUCER_OPERATIONS,producer_before_report_baseline=38,
        producer_without_unadmitted_report=107,producer_with_equivalent_report=109,
        issuer_calls_known=False,P1_guard_calls_known=False,fault_call_budget_complete=False,
        producer_workflow_admitted=False,wall_RSS_storage_admitted=False,run_authority=False,formal_result=False,actual_F=False)
