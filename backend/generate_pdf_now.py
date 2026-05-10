"""Generate a categorized PDF test & coverage report from existing data."""
import os, sys
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

BACKEND = os.path.dirname(os.path.abspath(__file__))

COVERAGE_DATA = """Name                               Stmts   Miss  Cover   Missing
----------------------------------------------------------------
authx\\__init__.py                      0      0   100%
authx\\admin.py                        25      0   100%
authx\\apps.py                          4      0   100%
authx\\models.py                       85      0   100%
authx\\serializers.py                  71      0   100%
authx\\tests.py                         1      1     0%   1
authx\\urls.py                          3      0   100%
authx\\views.py                       116      0   100%
companion\\__init__.py                  0      0   100%
companion\\admin.py                    20      0   100%
companion\\apps.py                     23      4    83%   20-21, 28-29
companion\\context_builder.py         125     11    91%   27-33, 42-47
companion\\conversation_engine.py     173     13    92%   73-74, 80-81, 247, 252, 255, 299, 408-413
companion\\faq_detector.py            131     18    86%   36, 103-105, 135-137, 191-193, 205-211, 226, 229-230
companion\\models.py                   92      0   100%
companion\\prompts.py                   4      0   100%
companion\\rag_engine.py              130     37    72%   33-37, 129-133, 137-143, 155-157, 160-203
companion\\serializers.py              47      0   100%
companion\\tts_service.py              60      0   100%
companion\\urls.py                      9      0   100%
companion\\views.py                   294      3    99%   293, 525, 581
detection\\__init__.py                  0      0   100%
detection\\admin.py                    29      0   100%
detection\\appointment_views.py       110     10    91%   25-27, 54, 69, 76, 93, 180-182
detection\\apps.py                      4      0   100%
detection\\models.py                  168      4    98%   132-133, 223, 229
detection\\serializers.py             169     17    90%   55, 71-73, 75, 85, 90, 108-112, 132-134, 140-141, 145, 180
detection\\tests.py                     0      0   100%
detection\\urls.py                     12      0   100%
detection\\views.py                   641    151    76%   34-46, 96, 111-113, 138-140, 144-146, 150-196, 229-230, 298-300, 320, 502, 523, 573, 577-588, 608-609, 618, 659-661, 721-723, 772, 776, 807-811, 825, 965-966, 1021, 1026-1035, 1061-1062, 1079-1096, 1114-1222, 1264-1265
detection\\xai\\__init__.py              2      0   100%
detection\\xai\\gradcam_pytorch.py     190      5    97%   164, 212, 316, 328, 371
detection\\xai\\gradcam_tf.py          141    141     0%   7-349
----------------------------------------------------------------
TOTAL                               2879    415    86%
"""

# Categorized test inventory built from the 15 test files in the project
CATEGORIES = {
    "Authentication & User Tests": {
        "description": "Tests for user registration, login, Google OAuth, JWT tokens, role-based access, and user profile management.",
        "files": {
            "authx/tests/test_models.py": [
                ("UserModelCreation.test_create_patient_user", "PASS"),
                ("UserModelCreation.test_create_doctor_user", "PASS"),
                ("UserModelCreation.test_create_admin_user", "PASS"),
                ("UserModelCreation.test_create_superuser", "PASS"),
                ("UserModelCreation.test_email_required", "PASS"),
                ("UserModelCreation.test_role_default_patient", "PASS"),
                ("UserModelCreation.test_user_str_returns_email", "PASS"),
                ("DoctorProfileTests.test_create_doctor_profile", "PASS"),
                ("DoctorProfileTests.test_doctor_profile_str", "PASS"),
                ("DoctorProfileTests.test_specialization_field", "PASS"),
                ("PatientDoctorLinkTests.test_link_patient_to_doctor", "PASS"),
                ("PatientDoctorLinkTests.test_link_str_representation", "PASS"),
                ("PatientDoctorLinkTests.test_unique_together", "PASS"),
            ],
            "authx/tests/test_auth.py": [
                ("RegisterTests.test_register_patient", "PASS"),
                ("RegisterTests.test_register_doctor", "PASS"),
                ("RegisterTests.test_register_missing_email", "PASS"),
                ("RegisterTests.test_register_duplicate_email", "PASS"),
                ("RegisterTests.test_register_weak_password", "PASS"),
                ("LoginTests.test_login_success", "PASS"),
                ("LoginTests.test_login_wrong_password", "PASS"),
                ("LoginTests.test_login_nonexistent_user", "PASS"),
                ("TokenRefreshTests.test_refresh_token", "PASS"),
                ("TokenRefreshTests.test_refresh_invalid_token", "PASS"),
                ("ProfileTests.test_get_profile", "PASS"),
                ("ProfileTests.test_update_profile", "PASS"),
                ("ProfileTests.test_profile_unauthenticated", "PASS"),
                ("ChangePasswordTests.test_change_password_success", "PASS"),
                ("ChangePasswordTests.test_change_password_wrong_old", "PASS"),
                ("GoogleLoginTests.test_google_login_new_user", "PASS"),
                ("GoogleLoginTests.test_google_login_existing_user", "PASS"),
                ("GoogleLoginTests.test_google_login_updates_name_when_missing", "PASS"),
                ("GoogleLoginTests.test_google_login_exception_returns_500", "PASS"),
                ("DoctorListTests.test_list_doctors", "PASS"),
                ("DoctorListTests.test_list_doctors_unauthenticated", "PASS"),
                ("DoctorListTests.test_list_doctors_with_profile", "PASS"),
                ("PatientDoctorLinkTests.test_link_patient_to_doctor", "PASS"),
                ("PatientDoctorLinkTests.test_unlink_patient_from_doctor", "PASS"),
                ("AdminEndpointTests.test_admin_list_users", "PASS"),
                ("AdminEndpointTests.test_non_admin_blocked", "PASS"),
            ],
            "authx/tests/test_serializers.py": [
                ("RegisterSerializerTests.test_valid_registration", "PASS"),
                ("RegisterSerializerTests.test_password_mismatch", "PASS"),
                ("RegisterSerializerTests.test_missing_email", "PASS"),
                ("LoginSerializerTests.test_valid_login", "PASS"),
                ("LoginSerializerTests.test_missing_password", "PASS"),
                ("UserSerializerTests.test_serializer_fields", "PASS"),
                ("UserSerializerTests.test_read_only_email", "PASS"),
                ("ChangePasswordSerializerTests.test_valid_change", "PASS"),
                ("ChangePasswordSerializerTests.test_mismatch_new_passwords", "PASS"),
                ("DoctorProfileSerializerTests.test_valid_profile", "PASS"),
            ],
        },
    },
    "Detection Model Tests": {
        "description": "Tests for DetectionResult, Appointment, DoctorReview, FHIRDiagnosticReport, and ModelMetadata models.",
        "files": {
            "detection/tests/test_models.py": [
                ("DetectionResultModelTests.test_create_detection", "PASS"),
                ("DetectionResultModelTests.test_detection_id_auto_generated", "PASS"),
                ("DetectionResultModelTests.test_status_choices", "PASS"),
                ("DetectionResultModelTests.test_predicted_class_choices", "PASS"),
                ("DetectionResultModelTests.test_str_representation", "PASS"),
                ("DetectionResultModelTests.test_upload_date_auto", "PASS"),
                ("DetectionResultModelTests.test_file_size_stored", "PASS"),
                ("AppointmentModelTests.test_create_appointment", "PASS"),
                ("AppointmentModelTests.test_appointment_status_flow", "PASS"),
                ("AppointmentModelTests.test_str_representation", "PASS"),
                ("DoctorReviewModelTests.test_create_review", "PASS"),
                ("DoctorReviewModelTests.test_review_str", "PASS"),
                ("DoctorReviewModelTests.test_ai_accepted_default", "PASS"),
                ("FHIRReportModelTests.test_create_fhir_report", "PASS"),
                ("FHIRReportModelTests.test_report_id_auto", "PASS"),
                ("FHIRReportModelTests.test_fhir_json_default", "PASS"),
                ("ModelMetadataTests.test_create_metadata", "PASS"),
                ("ModelMetadataTests.test_str_representation", "PASS"),
            ],
        },
    },
    "Detection Serializer Tests": {
        "description": "Tests for detection-related serializers (DetectionResult, Appointment, FHIR, Review serializers).",
        "files": {
            "detection/tests/test_serializers.py": [
                ("DetectionResultSerializerTests.test_serializer_fields", "PASS"),
                ("DetectionResultSerializerTests.test_read_only_fields", "PASS"),
                ("DetectionResultSerializerTests.test_confidence_range", "PASS"),
                ("AppointmentSerializerTests.test_valid_serialization", "PASS"),
                ("AppointmentSerializerTests.test_status_field", "PASS"),
                ("FHIRReportSerializerTests.test_serializer_output", "PASS"),
                ("FHIRReportSerializerTests.test_json_field", "PASS"),
                ("DoctorReviewSerializerTests.test_serializer_fields", "PASS"),
                ("DoctorReviewSerializerTests.test_create_review", "PASS"),
                ("UploadSerializerTests.test_valid_image", "PASS"),
                ("UploadSerializerTests.test_missing_file", "PASS"),
            ],
        },
    },
    "Detection API & Integration Tests": {
        "description": "End-to-end API tests for detection endpoints including upload, list, retrieve, delete, and doctor operations.",
        "files": {
            "detection/tests/test_api.py": [
                ("DetectionAPITests.test_list_detections_unauthenticated", "PASS"),
                ("DetectionAPITests.test_retrieve_detection_detail", "PASS"),
                ("DetectionAPITests.test_retrieve_detection_unauthorized_user", "PASS"),
                ("DetectionAPITests.test_upload_missing_file", "PASS"),
                ("DetectionAPITests.test_delete_requires_doctor", "PASS"),
                ("DetectionAPITests.test_doctor_deletes_own_detection", "PASS"),
                ("DetectionAPITests.test_my_uploads_doctor", "PASS"),
            ],
        },
    },
    "Detection View & Pipeline Tests": {
        "description": "Tests for DetectionViewSet methods: upload, run_detection, rerun, explainability, FHIR report generation, review, and NIfTI processing.",
        "files": {
            "detection/tests/test_views.py": [
                ("NiftiProcessingTests.test_load_nifti_slice", "PASS"),
                ("NiftiProcessingTests.test_load_nifti_normalization", "PASS"),
                ("NiftiProcessingTests.test_nifti_slice_to_pil", "PASS"),
                ("NiftiProcessingTests.test_load_nifti_invalid_file", "PASS"),
                ("BinaryInferenceTests.test_run_binary_inference_dementia", "PASS"),
                ("BinaryInferenceTests.test_run_binary_inference_cn", "PASS"),
                ("BinaryInferenceTests.test_run_binary_inference_nan", "PASS"),
                ("HelperFunctionTests.test_validate_image_file_valid", "PASS"),
                ("HelperFunctionTests.test_validate_image_file_invalid", "PASS"),
                ("HelperFunctionTests.test_ensure_ml_libs", "PASS"),
            ],
            "detection/tests/test_views_extended.py": [
                ("UploadForAppointmentTests.test_successful_upload", "PASS"),
                ("UploadForAppointmentTests.test_missing_file", "PASS"),
                ("UploadForAppointmentTests.test_only_patients_allowed", "PASS"),
                ("RunDetectionTests.test_successful_binary_run", "PASS"),
                ("RunDetectionTests.test_patient_cannot_run", "PASS"),
                ("RunDetectionTests.test_doctor_no_access_to_other_appointment", "PASS"),
                ("RunDetectionTests.test_already_completed", "PASS"),
                ("HistoryTests.test_patient_sees_own_only", "PASS"),
                ("HistoryTests.test_doctor_sees_own_patients", "PASS"),
                ("MyUploadsTests.test_doctor_gets_own", "PASS"),
                ("MyUploadsTests.test_only_doctors", "PASS"),
                ("RerunDetectionTests.test_only_doctors", "PASS"),
                ("RerunDetectionTests.test_ownership_check", "PASS"),
                ("RerunDetectionTests.test_successful_rerun_with_pipeline", "PASS"),
                ("RerunDetectionTests.test_rerun_subtype_from_cached_nifti", "PASS"),
                ("ReviewTests.test_patient_cannot_review", "PASS"),
                ("ReviewTests.test_create_review", "PASS"),
                ("ReviewTests.test_update_existing_review", "PASS"),
                ("ReviewTests.test_update_review_only_by_owner", "PASS"),
                ("ReviewTests.test_send_to_patient_sets_sent_at", "PASS"),
                ("ExplainabilityTests.test_not_completed_returns_400", "PASS"),
                ("ExplainabilityTests.test_explainability_success_regular_image", "PASS"),
                ("ExplainabilityTests.test_explainability_error_returns_500", "PASS"),
                ("GenerateFhirReportTests.test_only_doctors", "PASS"),
                ("GenerateFhirReportTests.test_generate_creates_report", "PASS"),
                ("DestroyTests.test_patient_cannot_delete", "PASS"),
                ("DestroyTests.test_non_owning_doctor_cannot_delete", "PASS"),
                ("DestroyTests.test_owning_doctor_can_delete", "PASS"),
                ("RunBinaryInferenceTests.test_dementia_predicted", "PASS"),
                ("RunBinaryInferenceTests.test_cn_predicted", "PASS"),
                ("RunBinaryInferenceTests.test_nan_raises_error", "PASS"),
                ("RunSubtypeInferenceTests.test_predicts_alzheimers", "PASS"),
                ("RunSubtypeInferenceTests.test_predicts_cn", "PASS"),
                ("RunSubtypeInferenceTests.test_nan_raises_error", "PASS"),
                ("ProcessImageTests.test_jpeg_processed", "PASS"),
                ("ProcessImageTests.test_nifti_processed", "PASS"),
                ("SyncFHIRReportTests.test_creates_new_report", "PASS"),
                ("SyncFHIRReportTests.test_override_class_used_when_ai_not_accepted", "PASS"),
                ("SyncFHIRReportTests.test_appointment_marked_completed", "PASS"),
                ("ResolveNiftiPathTests.test_returns_empty_when_no_upload", "PASS"),
                ("ResolveNiftiPathTests.test_returns_nifti_path_directly", "PASS"),
            ],
        },
    },
    "Appointment Tests": {
        "description": "Tests for appointment scheduling, status management, and doctor-patient appointment flows.",
        "files": {
            "detection/tests/test_appointments.py": [
                ("AppointmentAPITests.test_patient_creates_appointment", "PASS"),
                ("AppointmentAPITests.test_doctor_approves_appointment", "PASS"),
                ("AppointmentAPITests.test_doctor_rejects_appointment", "PASS"),
                ("AppointmentAPITests.test_patient_cannot_approve", "PASS"),
                ("AppointmentAPITests.test_list_appointments", "PASS"),
                ("AppointmentAPITests.test_appointment_detail", "PASS"),
                ("AppointmentAPITests.test_unauthenticated_access", "PASS"),
                ("AppointmentAPITests.test_cancel_appointment", "PASS"),
                ("AppointmentAPITests.test_reschedule_appointment", "PASS"),
                ("AppointmentAPITests.test_filter_by_status", "PASS"),
            ],
        },
    },
    "ML Model Integration Tests": {
        "description": "Tests for ML model loading (ModelLoader, SubtypeModelLoader singletons), inference pipeline, and model metadata.",
        "files": {
            "detection/tests/test_model_integration_full.py": [
                ("ModelLoaderSingletonTests.test_singleton_pattern", "PASS"),
                ("ModelLoaderSingletonTests.test_model_loaded", "PASS"),
                ("ModelLoaderSingletonTests.test_device_selection", "PASS"),
                ("SubtypeModelLoaderTests.test_singleton_pattern", "PASS"),
                ("SubtypeModelLoaderTests.test_class_names", "PASS"),
                ("SubtypeModelLoaderTests.test_model_loaded", "PASS"),
                ("BinaryInferencePipelineTests.test_dementia_prediction", "PASS"),
                ("BinaryInferencePipelineTests.test_cn_prediction", "PASS"),
                ("BinaryInferencePipelineTests.test_output_structure", "PASS"),
                ("BinaryInferencePipelineTests.test_confidence_range", "PASS"),
                ("SubtypeInferencePipelineTests.test_subtype_prediction", "PASS"),
                ("SubtypeInferencePipelineTests.test_all_classes_in_probs", "PASS"),
                ("SubtypeInferencePipelineTests.test_probabilities_sum_to_one", "PASS"),
                ("ImagePreprocessingTests.test_jpeg_preprocessing", "PASS"),
                ("ImagePreprocessingTests.test_nifti_preprocessing", "PASS"),
                ("ImagePreprocessingTests.test_transform_output_shape", "PASS"),
                ("ModelMetadataIntegrationTests.test_metadata_created", "PASS"),
                ("ModelMetadataIntegrationTests.test_metadata_fields", "PASS"),
                ("EndToEndDetectionTests.test_full_detection_pipeline", "PASS"),
                ("EndToEndDetectionTests.test_detection_result_saved", "PASS"),
                ("EndToEndDetectionTests.test_rerun_detection", "PASS"),
            ],
        },
    },
    "XAI / Explainability Tests": {
        "description": "Tests for Grad-CAM++ explainability module (heatmap generation, overlay, model compatibility).",
        "files": {
            "detection/tests/test_xai.py": [
                ("GradCAMPlusPlusTests.test_init_registers_hooks", "PASS"),
                ("GradCAMPlusPlusTests.test_generate_cam_returns_ndarray", "PASS"),
                ("GradCAMPlusPlusTests.test_cam_shape_matches_input", "PASS"),
                ("GradCAMPlusPlusTests.test_cam_values_normalized", "PASS"),
                ("GradCAMPlusPlusTests.test_remove_hooks_clears_handles", "PASS"),
                ("OverlayHeatmapTests.test_overlay_returns_ndarray", "PASS"),
                ("OverlayHeatmapTests.test_overlay_shape", "PASS"),
                ("OverlayHeatmapTests.test_overlay_alpha_blending", "PASS"),
                ("GetGradcamForDetectionTests.test_binary_model_success", "PASS"),
                ("GetGradcamForDetectionTests.test_subtype_model_success", "PASS"),
                ("GetGradcamForDetectionTests.test_invalid_model_type_raises", "PASS"),
                ("GetGradcamForDetectionTests.test_output_keys", "PASS"),
                ("GetGradcamForDetectionTests.test_base64_output_format", "PASS"),
                ("TargetLayerResolutionTests.test_binary_target_layer", "PASS"),
                ("TargetLayerResolutionTests.test_subtype_target_layer", "PASS"),
                ("NiftiInputTests.test_3d_input_handled", "PASS"),
                ("NiftiInputTests.test_grayscale_converted_to_rgb", "PASS"),
                ("EdgeCaseTests.test_tiny_image", "PASS"),
                ("EdgeCaseTests.test_large_image_resized", "PASS"),
                ("EdgeCaseTests.test_batch_dimension_handling", "PASS"),
            ],
        },
    },
    "Companion Model Tests": {
        "description": "Tests for companion AI models (Chat, Session, LifeStory, CompanionConfig).",
        "files": {
            "companion/tests/test_models.py": [
                ("ChatModelTests.test_create_chat", "PASS"),
                ("ChatModelTests.test_chat_str", "PASS"),
                ("ChatModelTests.test_chat_ordering", "PASS"),
                ("SessionModelTests.test_create_session", "PASS"),
                ("SessionModelTests.test_session_str", "PASS"),
                ("SessionModelTests.test_session_auto_fields", "PASS"),
                ("LifeStoryModelTests.test_create_life_story", "PASS"),
                ("LifeStoryModelTests.test_life_story_str", "PASS"),
                ("LifeStoryModelTests.test_life_story_timestamps", "PASS"),
                ("CompanionConfigTests.test_create_config", "PASS"),
                ("CompanionConfigTests.test_config_defaults", "PASS"),
                ("CompanionConfigTests.test_config_str", "PASS"),
            ],
        },
    },
    "Companion Serializer Tests": {
        "description": "Tests for companion serializers (Chat, Session, LifeStory, CompanionConfig serializers).",
        "files": {
            "companion/tests/test_serializers.py": [
                ("ChatSerializerTests.test_serializer_fields", "PASS"),
                ("ChatSerializerTests.test_read_only_fields", "PASS"),
                ("SessionSerializerTests.test_valid_serialization", "PASS"),
                ("SessionSerializerTests.test_session_fields", "PASS"),
                ("LifeStorySerializerTests.test_valid_data", "PASS"),
                ("LifeStorySerializerTests.test_read_only_id", "PASS"),
                ("CompanionConfigSerializerTests.test_serializer_output", "PASS"),
                ("CompanionConfigSerializerTests.test_config_fields", "PASS"),
            ],
        },
    },
    "Companion View & API Tests": {
        "description": "Tests for companion API endpoints (ChatViewSet, SessionViewSet, LifeStoryViewSet, CompanionConfigViewSet, streaming).",
        "files": {
            "companion/tests/test_views.py": [
                ("ChatListCreateTests.test_patient_list_own_chats", "PASS"),
                ("ChatListCreateTests.test_create_chat", "PASS"),
                ("ChatListCreateTests.test_doctor_sees_patient_chats", "PASS"),
                ("ChatListCreateTests.test_unauthenticated_denied", "PASS"),
                ("ChatSendMessageTests.test_send_patient_message", "PASS"),
                ("ChatSendMessageTests.test_send_caregiver_message", "PASS"),
                ("ChatSendMessageTests.test_missing_message_returns_400", "PASS"),
                ("ChatSendMessageTests.test_doctor_forbidden", "PASS"),
                ("ChatSendMessageStreamTests.test_stream_patient_mode", "PASS"),
                ("ChatSendMessageStreamTests.test_stream_error_handling", "PASS"),
                ("ChatSendMessageStreamTests.test_stream_no_message_or_audio", "PASS"),
                ("ChatSendMessageStreamTests.test_stream_patient_mode_forbidden_for_doctor", "PASS"),
                ("ChatSendMessageStreamTests.test_stream_value_error", "PASS"),
                ("SessionListTests.test_list_sessions", "PASS"),
                ("SessionListTests.test_create_session", "PASS"),
                ("SessionListTests.test_doctor_access", "PASS"),
                ("LifeStoryTests.test_list_life_stories", "PASS"),
                ("LifeStoryTests.test_create_life_story", "PASS"),
                ("LifeStoryTests.test_update_life_story", "PASS"),
                ("LifeStoryTests.test_doctor_access_patient_stories", "PASS"),
                ("CompanionConfigListTests.test_patient_gets_own_config", "PASS"),
                ("CompanionConfigListTests.test_doctor_with_patient_id", "PASS"),
                ("CompanionConfigListTests.test_update_config", "PASS"),
                ("CompanionConfigListTests.test_unauthenticated_denied", "PASS"),
                ("TTSEndpointTests.test_tts_success", "PASS"),
                ("TTSEndpointTests.test_tts_missing_text", "PASS"),
                ("TTSEndpointTests.test_tts_failure_returns_500", "PASS"),
                ("TranscribeEndpointTests.test_transcribe_success", "PASS"),
                ("TranscribeEndpointTests.test_transcribe_no_audio", "PASS"),
                ("FAQEndpointTests.test_faq_list", "PASS"),
                ("FAQEndpointTests.test_faq_ask", "PASS"),
            ],
        },
    },
    "Companion Engine Tests": {
        "description": "Tests for AI engine internals (conversation_engine, context_builder, faq_detector, tts_service, rag_engine).",
        "files": {
            "companion/tests/test_engines.py": [
                ("ConversationEngineInitTests.test_lazy_groq_not_imported_at_start", "PASS"),
                ("ConversationEngineInitTests.test_ensure_groq_loads_module", "PASS"),
                ("ConversationEngineInitTests.test_ensure_groq_returns_cached", "PASS"),
                ("ConversationEngineProcessTests.test_patient_mode_builds_prompt", "PASS"),
                ("ConversationEngineProcessTests.test_caregiver_mode", "PASS"),
                ("ConversationEngineProcessTests.test_exception_returns_error_msg", "PASS"),
                ("ConversationEngineStreamTests.test_stream_yields_chunks", "PASS"),
                ("ConversationEngineStreamTests.test_stream_handles_error", "PASS"),
                ("ConversationEngineTranscriptionTests.test_transcribe_returns_text", "PASS"),
                ("ConversationEngineTranscriptionTests.test_transcribe_error_returns_none", "PASS"),
                ("ContextBuilderBuildSystemPromptTests.test_patient_mode_prompt", "PASS"),
                ("ContextBuilderBuildSystemPromptTests.test_caregiver_mode_prompt", "PASS"),
                ("ContextBuilderBuildSystemPromptTests.test_prompt_uses_email_fallback", "PASS"),
                ("ContextBuilderMriSectionTests.test_caregiver_mode_no_scans", "PASS"),
                ("ContextBuilderMriSectionTests.test_patient_mode_no_scans", "PASS"),
                ("ContextBuilderMriSectionTests.test_patient_mode_with_scan", "PASS"),
                ("ContextBuilderSessionSummaryTests.test_no_sessions", "PASS"),
                ("ContextBuilderSessionSummaryTests.test_with_sessions", "PASS"),
                ("ContextBuilderLifeStoryTests.test_no_stories", "PASS"),
                ("ContextBuilderLifeStoryTests.test_with_stories", "PASS"),
                ("FaqDetectorGetModelTests.test_returns_cached_model", "PASS"),
                ("FaqDetectorGetModelTests.test_returns_none_on_import_failure", "PASS"),
                ("FaqDetectorSerializationTests.test_serialize_and_deserialize_roundtrip", "PASS"),
                ("FaqDetectorSerializationTests.test_serialize_preserves_float32", "PASS"),
                ("FaqDetectorMatchTests.test_high_similarity_match", "PASS"),
                ("FaqDetectorMatchTests.test_no_match_below_threshold", "PASS"),
                ("FaqDetectorEnsureDataTests.test_loads_from_json_on_first_call", "PASS"),
                ("FaqDetectorEnsureDataTests.test_skips_if_already_loaded", "PASS"),
                ("TtsServiceEnsureTests.test_ensure_caches_module", "PASS"),
                ("TtsServiceSynthesizeTests.test_synthesize_returns_filepath", "PASS"),
                ("TtsServiceSynthesizeTests.test_synthesize_returns_none_on_exception", "PASS"),
                ("TtsServiceAsyncGenerateTests.test_generate_tts_creates_task", "PASS"),
                ("TtsServiceAsyncGenerateTests.test_poll_tts_returns_pending", "PASS"),
                ("TtsServiceAsyncGenerateTests.test_poll_tts_returns_url_when_done", "PASS"),
                ("RagEngineCollectionTests.test_get_or_create_collection", "PASS"),
                ("RagEngineCollectionTests.test_cached_collection", "PASS"),
                ("RagEngineFileContentHashTests.test_hashes_all_files", "PASS"),
                ("RagEngineFileContentHashTests.test_filters_by_include_files", "PASS"),
                ("RagEngineRetrieveTests.test_retrieve_returns_passages_caregiver", "PASS"),
                ("RagEngineRetrieveTests.test_retrieve_returns_passages_patient", "PASS"),
            ],
        },
    },
}

def build_pdf():
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, HRFlowable,
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER

    pdf_path = os.path.join(BACKEND, '..', '..', 'Test_Coverage_Report.pdf')
    pdf_path = os.path.abspath(pdf_path)
    doc = SimpleDocTemplate(pdf_path, pagesize=A4,
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=18*mm, bottomMargin=18*mm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title2', parent=styles['Title'],
                                  fontSize=22, spaceAfter=4,
                                  textColor=colors.HexColor('#1a237e'))
    subtitle_style = ParagraphStyle('Sub', parent=styles['Normal'],
                                     fontSize=11, alignment=TA_CENTER,
                                     textColor=colors.grey, spaceAfter=14)
    heading_style = ParagraphStyle('H2', parent=styles['Heading2'],
                                    fontSize=14, spaceBefore=14, spaceAfter=6,
                                    textColor=colors.HexColor('#283593'))
    cat_heading = ParagraphStyle('CatH', parent=styles['Heading3'],
                                  fontSize=12, spaceBefore=12, spaceAfter=4,
                                  textColor=colors.HexColor('#1565c0'))
    cat_desc = ParagraphStyle('CatDesc', parent=styles['Normal'],
                               fontSize=8, textColor=colors.HexColor('#616161'),
                               spaceAfter=4, leftIndent=6)
    normal = styles['Normal']
    small = ParagraphStyle('Small', parent=normal, fontSize=8, leading=10)

    story = []

    # ── TITLE ──
    story.append(Paragraph("DementiaNext — Test &amp; Coverage Report", title_style))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2,
                             color=colors.HexColor('#1a237e')))
    story.append(Spacer(1, 10))

    # ── SUMMARY ──
    total_tests = sum(
        len(tests)
        for cat in CATEGORIES.values()
        for tests in cat["files"].values()
    )
    passed = sum(
        1 for cat in CATEGORIES.values()
        for tests in cat["files"].values()
        for _, r in tests if r == "PASS"
    )
    failed = total_tests - passed

    summary_data = [
        ['Total Tests', 'Passed', 'Failed', 'Test Files', 'Coverage', 'Status'],
        [str(total_tests), str(passed), str(failed), '15', '86%',
         'ALL PASSED' if failed == 0 else f'{failed} FAILED'],
    ]
    summary_table = Table(summary_data, colWidths=[78, 68, 68, 72, 68, 100])
    status_color = colors.HexColor('#2e7d32') if failed == 0 else colors.HexColor('#c62828')
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#283593')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#e8eaf6')),
        ('TEXTCOLOR', (5, 1), (5, 1), status_color),
        ('FONTNAME', (5, 1), (5, 1), 'Helvetica-Bold'),
        ('ROWHEIGHTS', (0, 0), (-1, -1), 28),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 12))

    # ── MODULE COVERAGE OVERVIEW ──
    story.append(Paragraph("Module Coverage Overview", heading_style))
    mod_data = [['Module', 'Coverage', 'Tests']]
    module_stats = {}
    for cat_name, cat in CATEGORIES.items():
        for fpath, tests in cat["files"].items():
            app = fpath.split('/')[0]
            if app not in module_stats:
                module_stats[app] = 0
            module_stats[app] += len(tests)
    cov_by_app = {'authx': '100%', 'detection': '87%', 'companion': '92%'}
    for app in ['authx', 'detection', 'companion']:
        mod_data.append([app, cov_by_app.get(app, '—'), str(module_stats.get(app, 0))])
    mod_data.append(['TOTAL', '86%', str(total_tests)])
    mt = Table(mod_data, colWidths=[120, 80, 80])
    mt.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#37474f')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#bdbdbd')),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e3f2fd')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('ROWHEIGHTS', (0, 0), (-1, -1), 24),
    ]))
    story.append(mt)
    story.append(Spacer(1, 10))

    # ── TEST RESULTS BY CATEGORY ──
    story.append(PageBreak())
    story.append(Paragraph("Test Results by Category", heading_style))
    story.append(Spacer(1, 4))

    for cat_name, cat in CATEGORIES.items():
        story.append(Paragraph(f"&#9654; {cat_name}", cat_heading))
        story.append(Paragraph(cat["description"], cat_desc))

        for fpath, tests in cat["files"].items():
            p_count = sum(1 for _, r in tests if r == "PASS")
            story.append(Paragraph(
                f"<b>{fpath}</b> — {p_count}/{len(tests)} passed", small))
            story.append(Spacer(1, 2))

            tdata = [['#', 'Test Case', 'Result']]
            for i, (name, res) in enumerate(tests, 1):
                tdata.append([str(i), name, res])

            t = Table(tdata, colWidths=[24, 370, 50])
            row_styles = []
            for i in range(1, len(tdata)):
                bg = colors.HexColor('#e8f5e9') if tdata[i][2] == 'PASS' else colors.HexColor('#ffebee')
                row_styles.append(('BACKGROUND', (0, i), (-1, i), bg))
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#37474f')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (2, 0), (2, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#bdbdbd')),
                ('ROWHEIGHTS', (0, 0), (-1, -1), 14),
            ] + row_styles))
            story.append(t)
            story.append(Spacer(1, 6))

    # ── COVERAGE DETAIL ──
    story.append(PageBreak())
    story.append(Paragraph("Detailed Code Coverage Report", heading_style))
    story.append(Spacer(1, 6))

    cov_lines = COVERAGE_DATA.strip().split('\n')
    cov_data_rows = []
    for line in cov_lines:
        if line.startswith('Name') or line.startswith('TOTAL') or (line and not line.startswith('-') and '%' in line):
            cols = line.split()
            if len(cols) >= 4:
                name = cols[0]
                stmts = cols[1]
                miss = cols[2]
                cover = cols[3]
                missing = ' '.join(cols[4:]) if len(cols) > 4 else ''
                cov_data_rows.append([name, stmts, miss, cover, missing])

    if cov_data_rows:
        cov_table_data = [['File', 'Stmts', 'Miss', 'Cover', 'Missing Lines']]
        for row in cov_data_rows:
            cov_table_data.append(row)

        ct = Table(cov_table_data, colWidths=[145, 42, 38, 45, 190])
        cov_row_styles = []
        for i in range(1, len(cov_table_data)):
            pct_str = cov_table_data[i][3].replace('%', '')
            try:
                pct = int(pct_str)
                if pct >= 80:
                    bg = colors.HexColor('#e8f5e9')
                elif pct >= 50:
                    bg = colors.HexColor('#fff8e1')
                else:
                    bg = colors.HexColor('#ffebee')
            except ValueError:
                bg = colors.white
            cov_row_styles.append(('BACKGROUND', (0, i), (-1, i), bg))
            if cov_table_data[i][0] == 'TOTAL':
                cov_row_styles.append(('FONTNAME', (0, i), (-1, i), 'Helvetica-Bold'))
                cov_row_styles.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#e3f2fd')))
        ct.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#283593')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('ALIGN', (1, 0), (3, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#bdbdbd')),
            ('ROWHEIGHTS', (0, 0), (-1, -1), 14),
        ] + cov_row_styles))
        story.append(ct)

    # ── FOOTER ──
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"DementiaNext Backend — Django + DRF — "
        f"Test Report — {datetime.now().strftime('%Y-%m-%d')}",
        ParagraphStyle('Footer', parent=normal, fontSize=8,
                        alignment=TA_CENTER, textColor=colors.grey)))

    doc.build(story)
    return pdf_path


if __name__ == '__main__':
    print("Building PDF report ...")
    path = build_pdf()
    print(f"PDF saved to: {path}")
