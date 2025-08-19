# Agent Scenarios

The agent can generate code across multiple language lanes. Each example uses
file fences (`file: path`) to create source and test files before invoking a
lane-specific tool.

## Python FastAPI + pytest

```text
file: app/main.py
from fastapi import FastAPI
app = FastAPI()

@app.get("/")
def read_root():
    return {"hello": "world"}

file: tests/test_main.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root():
    assert client.get("/").json() == {"hello": "world"}
```

`use:python_fastapi` → builds and runs `pytest`.

## Web (Node/Jest)

```text
file: package.json
{ "scripts": {"test": "jest"} }

file: index.js
module.exports = () => 'hi';

file: index.test.js
const fn = require('./index');
test('hi', () => expect(fn()).toBe('hi'));
```

`use:web_node` → runs `npm test`.

## Java (Maven)

```text
file: pom.xml
<project><modelVersion>4.0.0</modelVersion></project>

file: src/main/java/App.java
public class App { public static String hi() { return "hi"; } }

file: src/test/java/AppTest.java
import static org.junit.Assert.*;
import org.junit.Test;
public class AppTest {
  @Test public void testHi() { assertEquals("hi", App.hi()); }
}
```

`use:java_maven` → runs `mvn -q test`.

## .NET (NuGet + xUnit)

```text
file: project.csproj
<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup><PackageReference Include="xunit" Version="2.4.2" /></ItemGroup>
</Project>

file: Program.cs
public class Program { public static int Add(int a,int b)=>a+b; }

file: ProgramTests.cs
using Xunit;
public class ProgramTests {
  [Fact] public void Adds() => Assert.Equal(4, Program.Add(2,2));
}
```

`use:dotnet` → runs `dotnet test`.

## Android (Gradle)

```text
file: app/build.gradle
apply plugin: 'com.android.application'

file: app/src/main/java/MainActivity.java
package app; class MainActivity {}

file: app/src/test/java/MainTest.java
package app; class MainTest { }
```

`use:android` → runs `./gradlew test`.

## C++ (CMake + Catch2)

```text
file: CMakeLists.txt
cmake_minimum_required(VERSION 3.16)
project(app)
add_executable(app main.cpp)
add_subdirectory(tests)

file: main.cpp
int add(int a,int b){return a+b;}

file: tests/CMakeLists.txt
add_executable(tests test.cpp)
target_link_libraries(tests Catch2::Catch2WithMain)
add_test(NAME tests COMMAND tests)

file: tests/test.cpp
#include <catch2/catch_test_macros.hpp>
int add(int,int);
TEST_CASE("adds", "[add]") { REQUIRE(add(2,2)==4); }
```

`use:cpp_cmake` → runs `cmake && ctest`.
