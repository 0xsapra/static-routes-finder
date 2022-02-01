from os import walk
import os
import getopt, sys
from abc import abstractmethod
import re
import logging




class Options:
    def __init__(self): 
        self.extensions = {"java": True} # dict of extensions to look for. Defaults java
        self.directory = os.getcwd() # directory to begin with. Default current directory

    def setExtensions(self, extensions):

        if type(extensions) != dict:
            return

        if len(extensions.keys()) == 0:
            # we go with default
            pass
        else:
            self.extensions = extensions
        return
    
    def setDirectory(self, directory):
        if directory != "":
            if os.path.isdir(directory) != False:
                self.directory = directory
            else:
                logging.critical("Directory dont exist " + directory + " .. Defaulting to current directory")
        return

class FileParser():

    @abstractmethod
    def getRoutes(self, filePath): pass


class JavaFileParser(FileParser):

    def __init__(self):
        
        ###  Prefix finder
        self.regex_request_mapping = re.compile("""RequestMapping\s*\("(.*)"\)""") # RequestMapping\("([\/a-zA-Z0-9_-]*)"\) idk if this is correct
        self.regex_routes_prefix_without_path = re.compile("""(@Path)\s*\("(.+)\"\)\n[^\s-]""")
        # Example
        #     @API
        #     @Path("plutus")
        #     @Produces(MediaType.APPLICATION_JSON)
        
        

        ### VERBMAPPING("")
        # .... \s* add between mapping and ()
        self.regex_routes = re.compile('@(Patch|Get|Post|Put|Delete)Mapping\s*\(\s*(\s*path\s*=\s*|\s*value\s*=\s*)?"(.*)"') # previos @((Patch)Mapping|(Get)Mapping|(Post)Mapping|(Put)Mapping|(Delete)Mapping)\("(.+)\"\)
        self.regex_routes_edge_case = re.compile("""@(Patch|Get|Post|Put|Delete)Mapping\s*\n\s+""") 
        # Example
        #     @PostMapping
        #     // comment
        #     public @ResponseBody Order createOrder(@RequestBody @NonNull @Valid 
        
        
        ### PATH only.. DEVIL
        
        # self.regex_routes_path = re.compile("""@(POST|PATCH|PUT|DELETE|GET)\n\s+@Path\("(.+)\"\)""") # previous used # self.regex_routes_without_path = re.compile("""(@(POST)\n\s+@Path|@(PATCH)\n\s+@Path|@(PUT)\n\s+@Path|@(DELETE)\n\s+@Path|@(GET)\n\s+@Path)\("(.+)\"\)""")
        # Example
        #     @Post
        #     @Path("/s/s/s")
        #     public @ResponseBody Order createOrder(@RequestBody @NonNull @Valid 
       
        # self.regex_routes_path_edge_case = re.compile("""(@(POST|GET|PATCH|DELETE|PUT)\n\s+)(public|\/\/)""")
        self.regex_routes_path_with_all_edge_case = re.compile("""(@Path\s*\(\"(.*)\"\)|@(GET|POST|PUT|PATCH|DELETE))(.|\n)*?(public|@Path\s*\(\"(.*)\"\)|@(GET|POST|PUT|PATCH|DELETE))""")
        # Example
        #     @Post
        #     public @ResponseBody Order createOrder(@RequestBody @NonNull @Valid 

        

    def getRoutes(self, file_path):
        file_data = self.readFile(file_path)
        prefix = self.get_prefix(file_data, file_path)
        routes = self.get_routes_from_file(file_data, file_path, prefix)
        
        for i in range(len(routes)):
            routes[i][0] = (prefix + "/" + routes[i][0]).replace("//", "/")
        
        return routes

        
    def get_routes_from_file(self, file_data, file_path, prefix):
        routes = [] # [(routes, HTTP_VERB)]
        
        try:

            [routes.append([m.group(3), m.group(1).upper()]) for m in self.regex_routes.finditer(file_data)] # VERBMAPPING("")
            [routes.append(["/", m.group(1).upper()]) for m in self.regex_routes_edge_case.finditer(file_data)] # VERBMAPPING <- without ("")
            
            # [routes.append([m.group(2), m.group(1).upper()]) for m in self.regex_routes_without_path.finditer(file_data)] # @POST @PATH("/")
            # [routes.append(["/", m.group(2).upper()]) for m in self.regex_routes_without_path_edge_case.finditer(file_data)] # @POST <- without @PATH
            for m in self.regex_routes_path_with_all_edge_case.finditer(file_data): 
                http_verb = (m.group(3) or m.group(7))
                path = (m.group(2) or m.group(6) or "/")

                if http_verb == None:
                    if path == prefix:
                        # regex is not perfect so hacky trick here
                        continue
                    else:
                        logging.critical("[-] Regex Error for regex_routes_path_with_all_edge_case. Found no http verb for file " + file_path + " for group " + m.group())
                        continue

                routes.append([path, http_verb])

        except Exception as e:
            print("[-] get_routes_from_files Error while reading file",file_path)
            print("Error : ",e)

        return routes
    
    def get_prefix(self, file_data, file_path):
        prefix = ""
        
        matches = [m.group(1) for m in self.regex_request_mapping.finditer(file_data)] # RequestMapping
        

        if len(matches) == 0:
            matches = [m.group(2) for m in self.regex_routes_prefix_without_path.finditer(file_data)] # Path
        
        if len(matches) == 0:
            return prefix

        if len(matches) > 1:
            logging.critical("[-] JavaFileParser:getRoutes Found more than 1 requestMapping on " + file_path)
            prefix = matches[0]
        elif len(matches) == 1:
            prefix = matches[0]

        return prefix


    
    def readFile(self, filePath):
        
        with open(filePath, "r") as f:
            file_data = f.read()
        return file_data


class Scanner:
    def __init__(self, options):
        self.options = options
        self.extensionsFileParsers = {
            "java": JavaFileParser(), #instance of java extension parser 
        }
        self.files = []

    def scan(self):
        self.DirTraversalForExtensionOnlyFiles() # traverse the directory and get all files
        all_routes = {}

        for file_name in self.files:
            (_file, extension) = splitFileNameExtension(file_name)
            
            if extension in self.extensionsFileParsers:
                routes = self.extensionsFileParsers[extension].getRoutes(file_name) # routes = [ [HTTP_VERB, ROUTE] , [HTTP_VERB, ROUTE2] ...]
                all_routes[file_name] = routes
                if len(routes) > 0:
                    print("==================")
                    print(f"File -> {file_name}")

                    for route in all_routes[file_name]:
                        print(f"\t{route[1]} \t {route[0]}")
        
        
        
    
    def print_routes():

        return all_routes
    
    def DirTraversalForExtensionOnlyFiles(self):
        files = []

        for (dirpath, dirnames, file_names) in walk(self.options.directory):
            for file_name in file_names:
                (_file, extension) = splitFileNameExtension(file_name)
                if extension in self.options.extensions:
                    files.append(dirpath + "/" + file_name)
        
        self.files = files
        return

    
def parseOptions():
    
    options = Options()
    short_options = "e:d:"
    long_options = ["extension = ", "dir ="]
    arguments, values = getopt.getopt(sys.argv[1:], short_options, long_options)

    options_dict = {
        "e": {},
        "d": os.getcwd(),
    }

    for currentArgument, currentValue in arguments:
        if currentArgument in ("-e", "--extension"):
            options_dict["e"][currentValue] = True
             
        elif currentArgument in ("-d", "--dir"):
            options_dict["d"] = currentValue

    for arg in options_dict:
        if arg == "d":
            options.setDirectory(options_dict["d"])
        elif arg == "e":
            options.setExtensions(options_dict["e"])
    
    return options


def splitFileNameExtension(file_name):
    try:
        (_file, ext) =  file_name.rsplit(".", 1)
        return (_file, ext)
    except:
        return ("", "")
    

def main():
    options = parseOptions()
    scanner = Scanner(options)

    scanner.scan()

if __name__ == "__main__":
    main()