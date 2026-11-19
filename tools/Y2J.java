import com.fasterxml.jackson.databind.*;
import com.fasterxml.jackson.dataformat.yaml.YAMLFactory;
import java.io.File;
public class Y2J { public static void main(String[] a) throws Exception {
  JsonNode n = new ObjectMapper(new YAMLFactory()).readTree(new File(a[0]));
  new ObjectMapper().writerWithDefaultPrettyPrinter().writeValue(new File(a[1]), n); } }
