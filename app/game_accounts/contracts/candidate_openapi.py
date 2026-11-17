"""Synthetic examples for the candidate recovery wire; no runtime I/O."""
REQUEST_EXAMPLES = {'reconcile': {'summary': 'reconcile',
               'value': {'items': [{'command_id': '11111111-1111-4111-8111-111111111111',
                                    'character_id': '22222222-2222-4222-8222-222222222222',
                                    'expected_ownership_revision': 1,
                                    'expected_lifecycle_revision': 1,
                                    'expected_summary_versions': {'dealer': 1, 'support': 1},
                                    'trigger': 'automatic',
                                    'candidate_context': {'candidate_id': '33333333-3333-4333-8333-333333333333',
                                                          'expected_generation': 1,
                                                          'expected_policy_revision': 1,
                                                          'expected_settings_version': 1,
                                                          'purpose': 'automatic_candidate'}}]}},
 'manual_retry_excluded_or_nice_off': {'summary': 'manual_retry_excluded_or_nice_off',
                                       'value': {'items': [{'command_id': '55555555-5555-4555-8555-555555555555',
                                                            'character_id': '22222222-2222-4222-8222-222222222222',
                                                            'expected_ownership_revision': 1,
                                                            'expected_lifecycle_revision': 1,
                                                            'expected_summary_versions': {'dealer': 1,
                                                                                          'support': 1},
                                                            'trigger': 'manual',
                                                            'candidate_context': {'candidate_id': '33333333-3333-4333-8333-333333333333',
                                                                                  'expected_generation': 1,
                                                                                  'expected_policy_revision': 1,
                                                                                  'expected_settings_version': 1,
                                                                                  'purpose': 'manual_retry'}}]}}}

RESPONSE_EXAMPLES = {'ANALYSIS_CANDIDATE_NOT_FOUND': {'value': {'evaluated_at': '2026-11-17T09:00:00Z',
                                            'items': [{'command_id': '11111111-1111-4111-8111-111111111111',
                                                       'character_id': '22222222-2222-4222-8222-222222222222',
                                                       'state': 'failed',
                                                       'status': 404,
                                                       'retry': 'none',
                                                       'detected_role': None,
                                                       'result': None,
                                                       'error': {'code': 'ANALYSIS_CANDIDATE_NOT_FOUND',
                                                                 'message': 'ANALYSIS_CANDIDATE_NOT_FOUND',
                                                                 'request_id': '44444444-4444-4444-8444-444444444444',
                                                                 'retry_after_seconds': None,
                                                                 'retry_at': None}}]}},
 'ANALYSIS_CANDIDATE_IN_PROGRESS': {'value': {'evaluated_at': '2026-11-17T09:00:00Z',
                                              'items': [{'command_id': '11111111-1111-4111-8111-111111111111',
                                                         'character_id': '22222222-2222-4222-8222-222222222222',
                                                         'state': 'failed',
                                                         'status': 409,
                                                         'retry': 'none',
                                                         'detected_role': None,
                                                         'result': None,
                                                         'error': {'code': 'ANALYSIS_CANDIDATE_IN_PROGRESS',
                                                                   'message': 'ANALYSIS_CANDIDATE_IN_PROGRESS',
                                                                   'request_id': '44444444-4444-4444-8444-444444444444',
                                                                   'retry_after_seconds': None,
                                                                   'retry_at': None}}]}},
 'ANALYSIS_CANDIDATE_RETRY_REQUIRED': {'value': {'evaluated_at': '2026-11-17T09:00:00Z',
                                                 'items': [{'command_id': '11111111-1111-4111-8111-111111111111',
                                                            'character_id': '22222222-2222-4222-8222-222222222222',
                                                            'state': 'skipped',
                                                            'status': 200,
                                                            'retry': 'none',
                                                            'detected_role': None,
                                                            'result': None,
                                                            'error': {'code': 'ANALYSIS_CANDIDATE_RETRY_REQUIRED',
                                                                      'message': 'ANALYSIS_CANDIDATE_RETRY_REQUIRED',
                                                                      'request_id': '44444444-4444-4444-8444-444444444444',
                                                                      'retry_after_seconds': None,
                                                                      'retry_at': None}}]}},
 'ANALYSIS_CANDIDATE_COMPLETED': {'value': {'evaluated_at': '2026-11-17T09:00:00Z',
                                            'items': [{'command_id': '11111111-1111-4111-8111-111111111111',
                                                       'character_id': '22222222-2222-4222-8222-222222222222',
                                                       'state': 'skipped',
                                                       'status': 200,
                                                       'retry': 'none',
                                                       'detected_role': None,
                                                       'result': None,
                                                       'error': {'code': 'ANALYSIS_CANDIDATE_COMPLETED',
                                                                 'message': 'ANALYSIS_CANDIDATE_COMPLETED',
                                                                 'request_id': '44444444-4444-4444-8444-444444444444',
                                                                 'retry_after_seconds': None,
                                                                 'retry_at': None}}]}},
 'ANALYSIS_CANDIDATE_RECONCILED': {'value': {'evaluated_at': '2026-11-17T09:00:00Z',
                                             'items': [{'command_id': '11111111-1111-4111-8111-111111111111',
                                                        'character_id': '22222222-2222-4222-8222-222222222222',
                                                        'state': 'failed',
                                                        'status': 409,
                                                        'retry': 'new_command',
                                                        'detected_role': None,
                                                        'result': None,
                                                        'error': {'code': 'ANALYSIS_CANDIDATE_RECONCILED',
                                                                  'message': 'ANALYSIS_CANDIDATE_RECONCILED',
                                                                  'request_id': '44444444-4444-4444-8444-444444444444',
                                                                  'retry_after_seconds': None,
                                                                  'retry_at': None}}]}},
 'manual_retry_saved': {'value': {'evaluated_at': '2026-11-16T08:00:00Z',
                                  'items': [{'command_id': '55555555-5555-4555-8555-555555555555',
                                             'character_id': '22222222-2222-4222-8222-222222222222',
                                             'status': 200,
                                             'state': 'saved',
                                             'detected_role': 'support',
                                             'retry': 'none',
                                             'error': None,
                                             'result': {'character_id': '22222222-2222-4222-8222-222222222222',
                                                        'game_account_id': '66666666-6666-4666-8666-666666666666',
                                                        'ownership_revision': 1,
                                                        'lifecycle_revision': 1,
                                                        'role': 'support',
                                                        'analysis': {'version': 2,
                                                                     'saved_at': '2026-11-16T08:00:00Z',
                                                                     'summary': {'source': 'server_analysis',
                                                                                 'analysis_rules_version': 'lostparty-server-role-analysis-v1',
                                                                                 'analyzed_at': '2026-11-16T08:00:00Z',
                                                                                 'combat_power': '1200.50',
                                                                                 'item_level': '1700.00',
                                                                                 'combat_power_observed_at': '2026-11-16T08:00:00Z',
                                                                                 'item_level_observed_at': '2026-11-16T08:00:00Z',
                                                                                 'integrity_status': 'error',
                                                                                 'catalog_version': '2026.11.17.1',
                                                                                 'issues': [{'code': 'GEM_SLOT_COUNT',
                                                                                             'severity': 'error'},
                                                                                            {'code': 'GEM_UNAVAILABLE',
                                                                                             'severity': 'warning'},
                                                                                            {'code': 'ARK_GRID_MINIMUM',
                                                                                             'severity': 'error'},
                                                                                            {'code': 'RUNE_COUNT',
                                                                                             'severity': 'warning'}],
                                                                                 'observed_lifecycle_revision': 1},
                                                                     'detail': {'detection': {'status': 'detected',
                                                                                              'catalog_version': '2026.11.17.1',
                                                                                              'class_id': 'bard',
                                                                                              'branch_id': 'perfect_harmony',
                                                                                              'branch_display_name': '바드',
                                                                                              'detected_role': 'support',
                                                                                              'matched_tier1_node': '완벽한 '
                                                                                                                    '화음',
                                                                                              'matched_related_nodes': ['세레나데 '
                                                                                                                        '코드']},
                                                                                'rune_count': 0,
                                                                                'equipped_gem_count': 1,
                                                                                'gem_effects_source_available': True,
                                                                                'gems': [{'slot': 0,
                                                                                          'level': 10,
                                                                                          'target': '세레나데 '
                                                                                                    '스킬',
                                                                                          'descriptions': [],
                                                                                          'category': 'passive_or_identity',
                                                                                          'validation_status': 'unavailable'}],
                                                                                'ark_grid_core_points': [{'name': '질서의 '
                                                                                                                  '해 '
                                                                                                                  ': '
                                                                                                                  '계약 '
                                                                                                                  'fixture',
                                                                                                          'grade': '유물',
                                                                                                          'point': 17,
                                                                                                          'minimum_point': 14,
                                                                                                          'recommended_point': 17}],
                                                                                'ark_grid_conditions': [{'core_name': '질서의 '
                                                                                                                      '해 '
                                                                                                                      ': '
                                                                                                                      '계약 '
                                                                                                                      'fixture',
                                                                                                         'condition_text': '1티어 '
                                                                                                                           '완벽한 '
                                                                                                                           '화음 '
                                                                                                                           '활성화 '
                                                                                                                           '필요 '
                                                                                                                           '4티어 '
                                                                                                                           '세레나데 '
                                                                                                                           '코드 '
                                                                                                                           '활성화 '
                                                                                                                           '필요',
                                                                                                         'required_passive_names': ['완벽한 '
                                                                                                                                    '화음',
                                                                                                                                    '세레나데 '
                                                                                                                                    '코드'],
                                                                                                         'missing_passive_names': []}],
                                                                                'ark_grid_minimum': {'order_sun_point': 17,
                                                                                                     'order_moon_point': None,
                                                                                                     'required_point': 14},
                                                                                'notices': [{'code': 'rune_count',
                                                                                             'severity': 'warning',
                                                                                             'message': '장착된 '
                                                                                                        '룬이 '
                                                                                                        '0개입니다. '
                                                                                                        '일반 '
                                                                                                        '스킬 '
                                                                                                        '8개의 '
                                                                                                        '룬 '
                                                                                                        '설정을 '
                                                                                                        '확인해 '
                                                                                                        '주세요.'},
                                                                                            {'code': 'ark_grid_missing_order_moon',
                                                                                             'severity': 'warning',
                                                                                             'message': '질서의 '
                                                                                                        '달 '
                                                                                                        '코어가 '
                                                                                                        '없습니다. '
                                                                                                        '필수 '
                                                                                                        '14P '
                                                                                                        '효과를 '
                                                                                                        '확인해 '
                                                                                                        '주세요.'}]}}}}]}}}
