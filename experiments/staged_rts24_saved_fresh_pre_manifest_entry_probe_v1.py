"""Payload suffix concatenated after Core51 by the frozen UTF-16 compiler."""


def pre_manifest_entry_probe_main():
    owner=None;primary=None
    try:
        owner=open_bound_local_pre_entry_lease()
        require(type(owner) is LocalPreEntryLease and owner._resource.owner is owner,
            'same endpoint/Core creating owner required')
        bookend_pre_manifest_endpoint(owner)
    except BaseException as error:
        primary=error
        raise
    finally:
        if owner is not None:
            try:owner.close()
            except BaseException as cleanup:
                if primary is not None:raise cleanup from primary
                raise
    print(canonical(dict(schema='staged_saved_F_pre_manifest_entry_probe_v1',
        authority='DRAFT_NONAUTHORITATIVE',closed=True,full_role_entry_connected=False,
        run_authority=False,actual_F=False)).decode('ascii'))


if __name__=='__main__':pre_manifest_entry_probe_main()
