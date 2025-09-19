from fastapi import HTTPException, status

class ExceptionRaised(HTTPException):
    def __init__(
            self,
            status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail: str = "Internal server error",
            error: Exception = None
        ):
    
        if error:
            detail += f": {str(error)}"

        super().__init__(status_code=status_code, detail=detail)


class ExceptionDict:
    def __init__(self):
        self.exceptions_class = {
            "AccountNotFound": ExceptionRaised,
            "AccountRegistrationFailed": ExceptionRaised,
            "InvalidCredentials": ExceptionRaised,
            "UpdateFailed": ExceptionRaised,
            "NoTaskFound": ExceptionRaised,
            "RetrievingTasksFailed": ExceptionRaised,
            "DatabaseError": ExceptionRaised,
            "AccountDuplication": ExceptionRaised,
            "TaskCreationFailed": ExceptionRaised,
        }

        self.exceptions_details = {
            # Add more errors here
            "AccountNotFound": lambda: ExceptionRaised(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account/s not found"
            ),
            "AccountRegistrationFailed": lambda: ExceptionRaised(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account registration failed"
            ),
            "InvalidCredentials": lambda: ExceptionRaised(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid password"
            ),
            "UpdateFailed": lambda: ExceptionRaised(
                detail="Failed to update account"
            ),
            "NoTaskFound": lambda: ExceptionRaised(
                detail="No task found"
            ),
            "RetrievingTasksFailed": lambda: ExceptionRaised(
                detail="Retrieving tasks from database failed"
            ),
            "DatabaseError": lambda error=None: ExceptionRaised(
                detail="Database error",
                error=error
            ),
            "AccountDuplication": lambda error=None: ExceptionRaised(
                detail="Email already used in another account",
                error=error
            ),
            "TaskCreationFailed": lambda error=None: ExceptionRaised(
                detail="Creating a new task failed",
                error=error
            )
        }
    
    def get(self, name: str):
        return self.exceptions_details[name]()

    def get_class(self, name: str):
        return self.exceptions_class[name]
