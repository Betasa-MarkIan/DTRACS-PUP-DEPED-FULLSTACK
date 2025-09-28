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
            "InvalidCredentials": lambda: ExceptionRaised(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid password"
            ),
            "AccountNotFound": lambda: ExceptionRaised(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account/s not found"
            ),
            "NoTaskFound": lambda: ExceptionRaised(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No task found"
            ),
            "AccountDuplication": lambda error=None: ExceptionRaised(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already exist in another account",
                error=error
            ),
            "AccountRegistrationFailed": lambda: ExceptionRaised(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account registration failed"
            ),
            "UpdateFailed": lambda: ExceptionRaised(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update account"
            ),
            "DatabaseError": lambda error=None: ExceptionRaised(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error",
                error=error
            ),
            "RetrievingTasksFailed": lambda: ExceptionRaised(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Retrieving tasks from database failed"
            ),
            "TaskCreationFailed": lambda error=None: ExceptionRaised(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Creating a new task failed",
                error=error
            )
        } 
    def get(self, name: str, error: Exception = None):
        if error:
            return self.exceptions_details[name](error=error)
        else:
            return self.exceptions_details[name]()
        
    def get_class(self, name: str):
        return self.exceptions_class[name]
