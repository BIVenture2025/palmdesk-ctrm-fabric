CREATE PROCEDURE eng.usp_run_range @from_idx INT, @to_idx INT
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @i INT = @from_idx;
    DECLARE @d DATE;
    WHILE @i <= @to_idx
    BEGIN
        SET @d = (SELECT biz_date FROM ref.calendar WHERE day_index = @i);
        EXEC eng.usp_run_eod @d = @d, @as_of = @d, @restated = 0;
        SET @i = @i + 1;
    END
END
