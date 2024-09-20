CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


--ensure create extensions for vector and graph

-- LOAD  'age';
-- SET search_path = ag_catalog, "$user", public;
-- SELECT create_graph('funkybrain');