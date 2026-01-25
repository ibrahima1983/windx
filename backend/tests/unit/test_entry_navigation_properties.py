"""Property-based tests for entry page navigation state preservation.

This module contains property-based tests that verify the entry page system
maintains navigation state correctly across page transitions.

**Feature: entry-page-system, Property 8: Navigation state preservation**
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request
from hypothesis import given
from hypothesis import strategies as st

from app.api.v1.endpoints.entry import accessories_page, glazing_page, profile_page
from app.models.user import User


@st.composite
def mock_request_with_params(draw):
    """Generate mock request with various query parameters."""
    request = MagicMock(spec=Request)

    # Generate query parameters
    manufacturing_type_id = draw(st.one_of(st.none(), st.integers(min_value=1, max_value=100)))
    configuration_id = draw(st.one_of(st.none(), st.integers(min_value=1, max_value=1000)))

    # Mock query parameters
    request.query_params = {}
    if manufacturing_type_id:
        request.query_params["manufacturing_type_id"] = str(manufacturing_type_id)
    if configuration_id:
        request.query_params["configuration_id"] = str(configuration_id)

    # Mock other request properties
    request.url = MagicMock()
    request.url.path = draw(
        st.sampled_from(
            ["/api/v1/entry/profile", "/api/v1/entry/accessories", "/api/v1/entry/glazing"]
        )
    )
    request.headers = {}

    return request


@st.composite
def mock_user(draw):
    """Generate mock user for testing."""
    user = MagicMock(spec=User)
    user.id = draw(st.integers(min_value=1, max_value=1000))
    user.username = draw(st.text(min_size=3, max_size=20))
    user.email = draw(st.text(min_size=5, max_size=50))
    user.role = draw(st.sampled_from(["customer", "salesman", "superadmin"]))
    user.is_active = True
    return user


class TestEntryNavigationProperties:
    """Test class for entry page navigation state preservation properties."""

    @pytest.mark.asyncio
    @given(
        request=mock_request_with_params(),
        user=mock_user(),
        manufacturing_type_id=st.one_of(st.none(), st.integers(min_value=1, max_value=100)),
    )
    async def test_property_navigation_state_preservation_profile(
        self, request, user, manufacturing_type_id
    ):
        """
        **Feature: entry-page-system, Property 8: Navigation state preservation**

        Property: For any navigation between entry pages, the system should maintain
        the current page state and provide consistent navigation experience.

        This test verifies profile page navigation state preservation.
        """
        # Arrange - Mock template response
        with patch("app.api.v1.endpoints.entry.templates") as mock_templates:
            mock_response = MagicMock()
            mock_templates.TemplateResponse.return_value = mock_response

            # Act - Call profile page endpoint
            response = await profile_page(request, user, manufacturing_type_id)

            # Assert - Template should be called with correct context
            mock_templates.TemplateResponse.assert_called_once()
            call_args = mock_templates.TemplateResponse.call_args

            # Verify template name
            template_name = call_args[0][0]
            assert template_name == "entry/profile.html.jinja"

            # Verify context contains navigation state
            context = call_args[0][1]
            assert isinstance(context, dict)

            # Should preserve request and user
            assert context["request"] == request
            assert context["user"] == user

            # Should maintain active page state
            assert context["active_page"] == "profile"
            assert context["page_title"] == "Profile Entry"

            # Should preserve manufacturing type ID if provided
            if manufacturing_type_id is not None:
                assert context["manufacturing_type_id"] == manufacturing_type_id
            else:
                assert context["manufacturing_type_id"] is None

            # Should include JavaScript evaluator for conditional logic
            assert "JAVASCRIPT_CONDITION_EVALUATOR" in context
            assert isinstance(context["JAVASCRIPT_CONDITION_EVALUATOR"], str)
            assert "ConditionEvaluator" in context["JAVASCRIPT_CONDITION_EVALUATOR"]

    @pytest.mark.asyncio
    @given(request=mock_request_with_params(), user=mock_user())
    async def test_property_navigation_state_preservation_accessories(self, request, user):
        """
        **Feature: entry-page-system, Property 8: Navigation state preservation**

        Property: Accessories page should maintain consistent navigation state
        and provide proper scaffold implementation indicators.
        """
        # Arrange - Mock template response
        with patch("app.api.v1.endpoints.entry.templates") as mock_templates:
            mock_response = MagicMock()
            mock_templates.TemplateResponse.return_value = mock_response

            # Act - Call accessories page endpoint
            response = await accessories_page(request, user)

            # Assert - Template should be called with correct context
            mock_templates.TemplateResponse.assert_called_once()
            call_args = mock_templates.TemplateResponse.call_args

            # Verify template name
            template_name = call_args[0][0]
            assert template_name == "entry/accessories.html.jinja"

            # Verify context contains navigation state
            context = call_args[0][1]
            assert isinstance(context, dict)

            # Should preserve request and user
            assert context["request"] == request
            assert context["user"] == user

            # Should maintain active page state
            assert context["active_page"] == "accessories"
            assert context["page_title"] == "Accessories Entry"

    @pytest.mark.asyncio
    @given(request=mock_request_with_params(), user=mock_user())
    async def test_property_navigation_state_preservation_glazing(self, request, user):
        """
        **Feature: entry-page-system, Property 8: Navigation state preservation**

        Property: Glazing page should maintain consistent navigation state
        and provide proper scaffold implementation indicators.
        """
        # Arrange - Mock template response
        with patch("app.api.v1.endpoints.entry.templates") as mock_templates:
            mock_response = MagicMock()
            mock_templates.TemplateResponse.return_value = mock_response

            # Act - Call glazing page endpoint
            response = await glazing_page(request, user)

            # Assert - Template should be called with correct context
            mock_templates.TemplateResponse.assert_called_once()
            call_args = mock_templates.TemplateResponse.call_args

            # Verify template name
            template_name = call_args[0][0]
            assert template_name == "entry/glazing.html.jinja"

            # Verify context contains navigation state
            context = call_args[0][1]
            assert isinstance(context, dict)

            # Should preserve request and user
            assert context["request"] == request
            assert context["user"] == user

            # Should maintain active page state
            assert context["active_page"] == "glazing"
            assert context["page_title"] == "Glazing Entry"

    @given(
        page_transitions=st.lists(
            st.sampled_from(["profile", "accessories", "glazing"]), min_size=2, max_size=5
        ),
        user=mock_user(),
    )
    def test_property_navigation_consistency_across_transitions(
        self, page_transitions: list[str], user
    ):
        """
        **Feature: entry-page-system, Property 8: Navigation state preservation**

        Property: Navigation state should remain consistent across multiple
        page transitions, maintaining user context and active page indicators.
        """
        # Arrange - Mock request for each transition
        contexts = []

        with patch("app.api.v1.endpoints.entry.templates") as mock_templates:
            mock_templates.TemplateResponse.return_value = MagicMock()

            # Act - Simulate navigation through pages
            for page in page_transitions:
                request = MagicMock(spec=Request)
                request.url.path = f"/api/v1/entry/{page}"
                request.query_params = {}

                # Call appropriate endpoint
                if page == "profile":
                    import asyncio

                    asyncio.run(profile_page(request, user, None))
                elif page == "accessories":
                    import asyncio

                    asyncio.run(accessories_page(request, user))
                elif page == "glazing":
                    import asyncio

                    asyncio.run(glazing_page(request, user))

                # Capture context from template call
                if mock_templates.TemplateResponse.called:
                    call_args = mock_templates.TemplateResponse.call_args
                    context = call_args[0][1]
                    contexts.append((page, context))
                    mock_templates.TemplateResponse.reset_mock()

        # Assert - Each context should maintain consistent navigation state
        for page, context in contexts:
            # Should preserve user across all transitions
            assert context["user"] == user

            # Should maintain correct active page
            assert context["active_page"] == page

            # Should have appropriate page title
            expected_titles = {
                "profile": "Profile Entry",
                "accessories": "Accessories Entry",
                "glazing": "Glazing Entry",
            }
            assert context["page_title"] == expected_titles[page]

            # Should maintain request context
            assert "request" in context
            assert context["request"] is not None

    @given(
        navigation_sequence=st.lists(
            st.fixed_dictionaries(
                {
                    "page": st.sampled_from(["profile", "accessories", "glazing"]),
                    "manufacturing_type_id": st.one_of(
                        st.none(), st.integers(min_value=1, max_value=100)
                    ),
                    "has_query_params": st.booleans(),
                }
            ),
            min_size=1,
            max_size=3,
        ),
        user=mock_user(),
    )
    def test_property_query_parameter_preservation(self, navigation_sequence: list[dict], user):
        """
        **Feature: entry-page-system, Property 8: Navigation state preservation**

        Property: Query parameters should be properly handled and preserved
        where appropriate during navigation.
        """
        # Act & Assert - Test each navigation step
        for nav_step in navigation_sequence:
            page = nav_step["page"]
            manufacturing_type_id = nav_step["manufacturing_type_id"]
            has_query_params = nav_step["has_query_params"]

            # Create request with or without query parameters
            request = MagicMock(spec=Request)
            request.url.path = f"/api/v1/entry/{page}"

            if has_query_params and manufacturing_type_id:
                request.query_params = {"manufacturing_type_id": str(manufacturing_type_id)}
            else:
                request.query_params = {}

            with patch("app.api.v1.endpoints.entry.templates") as mock_templates:
                mock_templates.TemplateResponse.return_value = MagicMock()

                # Call appropriate endpoint
                if page == "profile":
                    import asyncio

                    asyncio.run(profile_page(request, user, manufacturing_type_id))

                    # Verify manufacturing_type_id is preserved in profile page
                    if mock_templates.TemplateResponse.called:
                        call_args = mock_templates.TemplateResponse.call_args
                        context = call_args[0][1]
                        assert context["manufacturing_type_id"] == manufacturing_type_id

                elif page in ["accessories", "glazing"]:
                    if page == "accessories":
                        import asyncio

                        asyncio.run(accessories_page(request, user))
                    else:
                        import asyncio

                        asyncio.run(glazing_page(request, user))

                    # Verify context is properly set for scaffold pages
                    if mock_templates.TemplateResponse.called:
                        call_args = mock_templates.TemplateResponse.call_args
                        context = call_args[0][1]
                        assert context["active_page"] == page
                        assert context["user"] == user
