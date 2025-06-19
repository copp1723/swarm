"""Error handling service"""
import logging
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class ErrorCategory(Enum):
    """Error categories for classification"""
    UNKNOWN_ERROR = "unknown_error"
    API_ERROR = "api_error"
    DATABASE_ERROR = "database_error"
    VALIDATION_ERROR = "validation_error"
    AUTHENTICATION_ERROR = "authentication_error"
    CONFIGURATION_ERROR = "configuration_error"
    MCP_ERROR = "mcp_error"

@dataclass
class ErrorContext:
    """Context for error handling"""
    error_category: ErrorCategory
    user_message: str
    technical_details: str
    recovery_suggestions: list
    metadata: Dict[str, Any]

class ErrorHandler:
    """Centralized error handling service"""
    
    def handle_error(self, exception: Exception, category: ErrorCategory, 
                    context: Dict[str, Any], session_id: Optional[str] = None) -> ErrorContext:
        """Handle an error and return context"""
        
        # Log the error
        logger.error(f"Error in {context.get('endpoint', 'unknown')}: {str(exception)}", 
                    exc_info=True, extra={'session_id': session_id})
        
        # Determine user-friendly message based on category
        user_message = self._get_user_message(category, exception)
        
        # Get recovery suggestions
        recovery_suggestions = self._get_recovery_suggestions(category)
        
        # Create error context
        error_context = ErrorContext(
            error_category=category,
            user_message=user_message,
            technical_details=str(exception),
            recovery_suggestions=recovery_suggestions,
            metadata=context
        )
        
        return error_context
    
    def _get_user_message(self, category: ErrorCategory, exception: Exception) -> str:
        """Get user-friendly error message"""
        messages = {
            ErrorCategory.API_ERROR: "An error occurred while processing your request. Please try again.",
            ErrorCategory.DATABASE_ERROR: "Unable to access data. Please try again later.",
            ErrorCategory.VALIDATION_ERROR: "Invalid input provided. Please check your data.",
            ErrorCategory.AUTHENTICATION_ERROR: "Authentication failed. Please check your credentials.",
            ErrorCategory.CONFIGURATION_ERROR: "System configuration error. Please contact support.",
            ErrorCategory.MCP_ERROR: "MCP server error. Please check server status.",
            ErrorCategory.UNKNOWN_ERROR: "An unexpected error occurred. Please try again."
        }
        return messages.get(category, messages[ErrorCategory.UNKNOWN_ERROR])
    
    def _get_recovery_suggestions(self, category: ErrorCategory) -> list:
        """Get recovery suggestions for the error"""
        suggestions = {
            ErrorCategory.API_ERROR: [
                "Check your internet connection",
                "Verify API keys are configured",
                "Try again in a few moments"
            ],
            ErrorCategory.DATABASE_ERROR: [
                "Refresh the page",
                "Check database connection",
                "Contact system administrator"
            ],
            ErrorCategory.VALIDATION_ERROR: [
                "Review input requirements",
                "Check data format",
                "Ensure all required fields are filled"
            ],
            ErrorCategory.AUTHENTICATION_ERROR: [
                "Verify your credentials",
                "Check API key configuration",
                "Ensure permissions are correct"
            ],
            ErrorCategory.CONFIGURATION_ERROR: [
                "Review configuration files",
                "Check environment variables",
                "Restart the application"
            ],
            ErrorCategory.MCP_ERROR: [
                "Check MCP server status",
                "Restart MCP servers",
                "Review MCP configuration"
            ],
            ErrorCategory.UNKNOWN_ERROR: [
                "Try again",
                "Check logs for details",
                "Contact support if issue persists"
            ]
        }
        return suggestions.get(category, suggestions[ErrorCategory.UNKNOWN_ERROR])

# Global error handler instance
error_handler = ErrorHandler()